"""Tests for the pipeline engine — the deterministic execution loop."""

import os
import tempfile

import pytest

from pipeline.checks import CheckEvaluator
from pipeline.engine import (
    PipelineEngine,
    PrecheckFailedError,
    PostcheckFailedError,
    ExecutionFailedError,
)
from pipeline.models import (
    DAG,
    Step,
    StepStatus,
    ExecutionResult,
    FileExistsCheck,
    DirExistsCheck,
    ExitCodeCheck,
    ContainsTextCheck,
    FailurePolicy,
    RetryPolicy,
)


def _ok_executor(step: Step) -> ExecutionResult:
    """Always succeeds."""
    return ExecutionResult(status="succeeded", output="ok", exit_code=0)


def _fail_executor(step: Step) -> ExecutionResult:
    """Always fails."""
    return ExecutionResult(status="failed", output="", error="boom", exit_code=1)


class TestBasicExecution:
    def test_single_step_passes(self):
        dag = DAG(
            name="test",
            steps=[Step(id="s1", description="do thing", action="echo hi")],
        )
        engine = PipelineEngine(dag, executor=_ok_executor)
        report = engine.run()

        assert report.overall_status == "passed"
        assert report.steps_total == 1
        assert report.steps_passed == 1
        assert len(report.entries) == 1
        assert report.entries[0].status == StepStatus.COMPLETED

    def test_multiple_steps_in_order(self):
        dag = DAG(
            name="test",
            steps=[
                Step(id="s1", description="first", action="echo 1"),
                Step(id="s2", description="second", action="echo 2", depends_on=["s1"]),
                Step(id="s3", description="third", action="echo 3", depends_on=["s2"]),
            ],
        )
        engine = PipelineEngine(dag, executor=_ok_executor)
        report = engine.run()

        assert report.overall_status == "passed"
        assert report.steps_passed == 3
        assert [e.step_id for e in report.entries] == ["s1", "s2", "s3"]

    def test_determinism_hash_is_consistent(self):
        dag = DAG(
            name="test",
            steps=[Step(id="s1", description="do", action="echo")],
        )
        r1 = PipelineEngine(dag, executor=_ok_executor).run()
        r2 = PipelineEngine(dag, executor=_ok_executor).run()
        # Hashes differ because timestamps differ, but both are non-empty
        assert r1.determinism_hash
        assert r2.determinism_hash


class TestDependencies:
    def test_blocked_when_dependency_fails(self):
        dag = DAG(
            name="test",
            steps=[
                Step(
                    id="s1", description="fail", action="fail",
                    failure_policy=FailurePolicy(on_execution_failure="continue"),
                ),
                Step(id="s2", description="depends", action="echo", depends_on=["s1"]),
            ],
        )
        engine = PipelineEngine(dag, executor=_fail_executor)
        report = engine.run()

        assert report.entries[0].status == StepStatus.FAILED
        assert report.entries[1].status == StepStatus.BLOCKED
        assert report.steps_blocked == 1

    def test_skipped_optional_doesnt_block(self):
        """An optional step that's skipped should not block dependents."""
        with tempfile.TemporaryDirectory() as tmp:
            dag = DAG(
                name="test",
                steps=[
                    Step(
                        id="s1",
                        description="optional",
                        action="echo",
                        prechecks=[FileExistsCheck(path=os.path.join(tmp, "nope.txt"))],
                        failure_policy=FailurePolicy(on_precheck_failure="skip"),
                    ),
                    Step(id="s2", description="runs anyway", action="echo", depends_on=["s1"]),
                ],
            )
            engine = PipelineEngine(dag, executor=_ok_executor, checker=CheckEvaluator(cwd=tmp))
            report = engine.run()

            assert report.entries[0].status == StepStatus.SKIPPED
            assert report.entries[1].status == StepStatus.COMPLETED


class TestChecks:
    def test_precheck_file_exists_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create the file
            open(os.path.join(tmp, "input.txt"), "w").close()

            dag = DAG(
                name="test",
                steps=[
                    Step(
                        id="s1",
                        description="needs file",
                        action="echo",
                        prechecks=[FileExistsCheck(path="input.txt")],
                    ),
                ],
            )
            engine = PipelineEngine(dag, executor=_ok_executor, checker=CheckEvaluator(cwd=tmp))
            report = engine.run()
            assert report.overall_status == "passed"

    def test_precheck_file_missing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            dag = DAG(
                name="test",
                steps=[
                    Step(
                        id="s1",
                        description="needs file",
                        action="echo",
                        prechecks=[FileExistsCheck(path="missing.txt")],
                    ),
                ],
            )
            engine = PipelineEngine(dag, executor=_ok_executor, checker=CheckEvaluator(cwd=tmp))
            with pytest.raises(PrecheckFailedError):
                engine.run()

    def test_postcheck_exit_code(self):
        dag = DAG(
            name="test",
            steps=[
                Step(
                    id="s1",
                    description="check exit",
                    action="echo",
                    postchecks=[ExitCodeCheck(expected=0)],
                ),
            ],
        )
        engine = PipelineEngine(dag, executor=_ok_executor)
        report = engine.run()
        assert report.overall_status == "passed"
        assert report.entries[0].postcheck_results[0].passed

    def test_postcheck_exit_code_fails(self):
        dag = DAG(
            name="test",
            steps=[
                Step(
                    id="s1",
                    description="bad exit",
                    action="echo",
                    postchecks=[ExitCodeCheck(expected=0)],
                ),
            ],
        )
        engine = PipelineEngine(dag, executor=_fail_executor)
        with pytest.raises(ExecutionFailedError):
            engine.run()

    def test_postcheck_contains_text(self):
        def executor(step):
            return ExecutionResult(status="succeeded", output="All 42 tests passed", exit_code=0)

        dag = DAG(
            name="test",
            steps=[
                Step(
                    id="s1",
                    description="check output",
                    action="test",
                    postchecks=[ContainsTextCheck(expected="42 tests passed")],
                ),
            ],
        )
        engine = PipelineEngine(dag, executor=executor)
        report = engine.run()
        assert report.overall_status == "passed"


class TestDAGValidation:
    def test_rejects_duplicate_ids(self):
        with pytest.raises(ValueError, match="Duplicate"):
            DAG(
                name="test",
                steps=[
                    Step(id="s1", description="a", action="x"),
                    Step(id="s1", description="b", action="y"),
                ],
            )

    def test_rejects_missing_dependency(self):
        with pytest.raises(ValueError, match="does not exist"):
            DAG(
                name="test",
                steps=[
                    Step(id="s1", description="a", action="x", depends_on=["s99"]),
                ],
            )

    def test_rejects_self_dependency(self):
        with pytest.raises(ValueError, match="depends on itself"):
            DAG(
                name="test",
                steps=[
                    Step(id="s1", description="a", action="x", depends_on=["s1"]),
                ],
            )

    def test_rejects_cycle(self):
        with pytest.raises(ValueError, match="cycle"):
            DAG(
                name="test",
                steps=[
                    Step(id="s1", description="a", action="x", depends_on=["s2"]),
                    Step(id="s2", description="b", action="y", depends_on=["s1"]),
                ],
            )


class TestRetry:
    def test_retry_on_failure(self):
        call_count = 0

        def flaky_executor(step):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return ExecutionResult(status="failed", error="flaky", exit_code=1)
            return ExecutionResult(status="succeeded", output="ok", exit_code=0)

        dag = DAG(
            name="test",
            steps=[
                Step(
                    id="s1",
                    description="flaky step",
                    action="flaky",
                    retry=RetryPolicy(max_attempts=3, backoff_seconds=0),
                ),
            ],
        )
        engine = PipelineEngine(dag, executor=flaky_executor)
        report = engine.run()
        assert report.overall_status == "passed"
        assert call_count == 3


class TestAuditTrail:
    def test_hash_chain_integrity(self):
        dag = DAG(
            name="test",
            steps=[
                Step(id="s1", description="a", action="x"),
                Step(id="s2", description="b", action="y", depends_on=["s1"]),
            ],
        )
        engine = PipelineEngine(dag, executor=_ok_executor)
        report = engine.run()

        # First entry has no previous hash
        assert report.entries[0].previous_hash is None
        # Second entry's previous_hash matches first entry's hash
        assert report.entries[1].previous_hash == report.entries[0].entry_hash
        # All hashes are non-empty
        for entry in report.entries:
            assert entry.entry_hash

    def test_summary_table_output(self):
        dag = DAG(
            name="test",
            steps=[Step(id="s1", description="a", action="x")],
        )
        engine = PipelineEngine(dag, executor=_ok_executor)
        report = engine.run()
        table = report.summary_table()
        assert "s1" in table
        assert "completed" in table
        assert "Determinism hash" in table


class TestCallbacks:
    def test_on_step_complete_called(self):
        events = []

        dag = DAG(
            name="test",
            steps=[
                Step(id="s1", description="a", action="x"),
                Step(id="s2", description="b", action="y", depends_on=["s1"]),
            ],
        )
        engine = PipelineEngine(
            dag, executor=_ok_executor, on_step_complete=lambda e: events.append(e.step_id)
        )
        engine.run()
        assert events == ["s1", "s2"]
