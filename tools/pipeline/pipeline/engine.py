"""Deterministic pipeline execution engine — the core loop.

This is the 'Option C' harness: code drives the loop, AI provides intelligence.
The engine guarantees every step is visited, checked, and audited.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from pipeline.checks import CheckEvaluator
from pipeline.models import (
    AuditEntry,
    DAG,
    ExecutionReport,
    ExecutionResult,
    Step,
    StepStatus,
    _topological_sort,
)


class PrecheckFailedError(Exception):
    def __init__(self, step: Step, results: list):
        self.step = step
        self.results = results
        super().__init__(f"Precheck failed for step '{step.id}'")


class PostcheckFailedError(Exception):
    def __init__(self, step: Step, results: list):
        self.step = step
        self.results = results
        super().__init__(f"Postcheck failed for step '{step.id}'")


class ExecutionFailedError(Exception):
    def __init__(self, step: Step, result: ExecutionResult):
        self.step = step
        self.result = result
        super().__init__(f"Execution failed for step '{step.id}': {result.error}")


# Type alias for the executor callable
Executor = Callable[[Step], ExecutionResult]


class PipelineEngine:
    """Deterministic pipeline executor.

    The engine walks a DAG in topological order. For each step:
      1. Verify all dependencies completed
      2. Run prechecks
      3. Execute the step (via the provided executor callable)
      4. Run postchecks
      5. Record an immutable audit entry

    The executor callable receives a Step and returns an ExecutionResult.
    It can be an AI call, a shell command, or any custom logic.
    """

    def __init__(
        self,
        dag: DAG,
        executor: Executor,
        checker: Optional[CheckEvaluator] = None,
        on_step_complete: Optional[Callable[[AuditEntry], None]] = None,
    ):
        self.dag = dag
        self.executor = executor
        self.checker = checker or CheckEvaluator()
        self.on_step_complete = on_step_complete
        self._audit: list[AuditEntry] = []
        self._step_statuses: dict[str, StepStatus] = {
            s.id: StepStatus.PENDING for s in dag.steps
        }

    def run(self) -> ExecutionReport:
        """Execute the full pipeline. Returns an ExecutionReport."""
        run_start = _now_iso()
        ordered = _topological_sort(self.dag.steps)

        for step in ordered:
            self._execute_step(step)

        run_end = _now_iso()
        return self._build_report(run_start, run_end)

    def _execute_step(self, step: Step) -> None:
        """Execute a single step with retries, prechecks, postchecks."""
        # 1. Check if dependencies are satisfied
        if not self._dependencies_satisfied(step):
            entry = self._record(step, StepStatus.BLOCKED, [], [])
            self._notify(entry)
            return

        # Retry loop
        last_entry: Optional[AuditEntry] = None
        for attempt in range(1, step.retry.max_attempts + 1):
            start_time = _now_iso()

            # 2. Prechecks
            precheck_results = self.checker.evaluate(step.prechecks)
            if not all(r.passed for r in precheck_results):
                policy = step.failure_policy.on_precheck_failure
                if policy == "skip":
                    last_entry = self._record(
                        step, StepStatus.SKIPPED, precheck_results, [], attempt=attempt
                    )
                    self._notify(last_entry)
                    return
                elif attempt < step.retry.max_attempts and "precheck_failed" in step.retry.retry_on:
                    time.sleep(step.retry.backoff_seconds)
                    continue
                else:
                    last_entry = self._record(
                        step, StepStatus.PRECHECK_FAILED, precheck_results, [], attempt=attempt
                    )
                    self._notify(last_entry)
                    if policy == "fail":
                        raise PrecheckFailedError(step, precheck_results)
                    return

            # 3. Execute
            self._step_statuses[step.id] = StepStatus.RUNNING
            try:
                exec_result = self.executor(step)
            except Exception as e:
                exec_result = ExecutionResult(
                    status="failed",
                    error=str(e),
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                )

            if exec_result.status == "failed":
                policy = step.failure_policy.on_execution_failure
                if attempt < step.retry.max_attempts and "executor_error" in step.retry.retry_on:
                    time.sleep(step.retry.backoff_seconds)
                    continue
                else:
                    last_entry = self._record(
                        step, StepStatus.FAILED, precheck_results, [],
                        output=exec_result.output, error=exec_result.error, attempt=attempt,
                    )
                    self._notify(last_entry)
                    if policy == "fail":
                        raise ExecutionFailedError(step, exec_result)
                    return

            if exec_result.status == "timeout":
                last_entry = self._record(
                    step, StepStatus.TIMEOUT, precheck_results, [],
                    output=exec_result.output, error="Execution timed out", attempt=attempt,
                )
                self._notify(last_entry)
                raise ExecutionFailedError(step, exec_result)

            # 4. Postchecks
            postcheck_results = self.checker.evaluate(step.postchecks, exec_result)
            if not all(r.passed for r in postcheck_results):
                policy = step.failure_policy.on_postcheck_failure
                if attempt < step.retry.max_attempts and "postcheck_failed" in step.retry.retry_on:
                    time.sleep(step.retry.backoff_seconds)
                    continue
                else:
                    last_entry = self._record(
                        step, StepStatus.POSTCHECK_FAILED, precheck_results, postcheck_results,
                        output=exec_result.output, attempt=attempt,
                    )
                    self._notify(last_entry)
                    if policy == "fail":
                        raise PostcheckFailedError(step, postcheck_results)
                    return

            # 5. Success!
            last_entry = self._record(
                step, StepStatus.COMPLETED, precheck_results, postcheck_results,
                output=exec_result.output, attempt=attempt,
            )
            self._notify(last_entry)
            return

    def _dependencies_satisfied(self, step: Step) -> bool:
        for dep_id in step.depends_on:
            status = self._step_statuses.get(dep_id, StepStatus.PENDING)
            if status != StepStatus.COMPLETED:
                # Allow skipped optional deps
                dep_step = next((s for s in self.dag.steps if s.id == dep_id), None)
                if dep_step and status == StepStatus.SKIPPED:
                    continue
                return False
        return True

    def _record(
        self,
        step: Step,
        status: StepStatus,
        prechecks: list,
        postchecks: list,
        output: str = "",
        error: Optional[str] = None,
        attempt: int = 1,
    ) -> AuditEntry:
        prev_hash = self._audit[-1].entry_hash if self._audit else None
        entry = AuditEntry(
            step_id=step.id,
            attempt=attempt,
            status=status,
            started_at=_now_iso(),
            completed_at=_now_iso(),
            precheck_results=prechecks,
            postcheck_results=postchecks,
            execution_output=output[:2000],  # cap output size
            error=error,
            previous_hash=prev_hash,
        )
        entry.entry_hash = entry.compute_hash()
        self._audit.append(entry)
        self._step_statuses[step.id] = status
        return entry

    def _notify(self, entry: AuditEntry) -> None:
        if self.on_step_complete:
            self.on_step_complete(entry)

    def _build_report(self, started_at: str, completed_at: str) -> ExecutionReport:
        passed = sum(1 for e in self._audit if e.status == StepStatus.COMPLETED)
        failed = sum(
            1 for e in self._audit
            if e.status in (StepStatus.FAILED, StepStatus.PRECHECK_FAILED,
                            StepStatus.POSTCHECK_FAILED, StepStatus.TIMEOUT)
        )
        blocked = sum(1 for e in self._audit if e.status == StepStatus.BLOCKED)
        skipped = sum(1 for e in self._audit if e.status == StepStatus.SKIPPED)

        if failed > 0:
            overall = "failed"
        elif blocked > 0 or skipped > 0:
            overall = "partial"
        else:
            overall = "passed"

        # Determinism hash: hash the full chain
        chain = json.dumps(
            [e.model_dump(mode="json") for e in self._audit],
            sort_keys=True,
            default=str,
        )
        det_hash = hashlib.sha256(chain.encode()).hexdigest()[:16]

        return ExecutionReport(
            dag_name=self.dag.name,
            started_at=started_at,
            completed_at=completed_at,
            overall_status=overall,
            entries=self._audit,
            steps_total=len(self.dag.steps),
            steps_passed=passed,
            steps_failed=failed,
            steps_blocked=blocked,
            steps_skipped=skipped,
            determinism_hash=det_hash,
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
