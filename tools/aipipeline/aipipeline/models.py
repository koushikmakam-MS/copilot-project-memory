"""Data models for the AI Pipeline Executor."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Step status
# ---------------------------------------------------------------------------

class StepStatus(str, Enum):
    PENDING = "pending"
    PRECHECK_FAILED = "precheck_failed"
    RUNNING = "running"
    POSTCHECK_FAILED = "postcheck_failed"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Typed checks — each check type is its own model
# ---------------------------------------------------------------------------

class BaseCheck(BaseModel):
    """Common fields for all checks."""
    description: str = ""
    verification_strength: str = "deterministic"


class FileExistsCheck(BaseCheck):
    """Verify a file exists at a given path."""
    type: str = "file_exists"
    path: str


class DirExistsCheck(BaseCheck):
    """Verify a directory exists."""
    type: str = "dir_exists"
    path: str


class ExitCodeCheck(BaseCheck):
    """Verify the execution exit code."""
    type: str = "exit_code"
    expected: int = 0


class ContainsTextCheck(BaseCheck):
    """Verify output contains expected text."""
    type: str = "contains_text"
    source: str = "stdout"  # stdout | stderr | file:<path>
    expected: str = ""


class CommandCheck(BaseCheck):
    """Run a command and verify its exit code is 0."""
    type: str = "command"
    command: str = ""


class CustomCheck(BaseCheck):
    """User-provided callable check. Not serializable to YAML."""
    type: str = "custom"
    verification_strength: str = "custom"
    check_fn: Any = None

    model_config = {"arbitrary_types_allowed": True}


# Union of all check types
Check = Union[
    FileExistsCheck,
    DirExistsCheck,
    ExitCodeCheck,
    ContainsTextCheck,
    CommandCheck,
    CustomCheck,
]


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

class RetryPolicy(BaseModel):
    max_attempts: int = 1
    backoff_seconds: float = 2.0
    retry_on: list[str] = ["executor_error", "postcheck_failed"]


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

class FailurePolicy(BaseModel):
    on_precheck_failure: str = "fail"   # fail | skip
    on_execution_failure: str = "fail"  # fail | continue
    on_postcheck_failure: str = "fail"  # fail | continue


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

class Step(BaseModel):
    """A single atomic unit of work in the pipeline."""
    id: str
    description: str
    depends_on: list[str] = []
    prechecks: list[Check] = []
    action: str  # instruction or command to execute
    postchecks: list[Check] = []
    failure_policy: FailurePolicy = FailurePolicy()
    retry: RetryPolicy = RetryPolicy()
    timeout_seconds: int = 300

    @field_validator("id")
    @classmethod
    def id_must_be_slug(cls, v: str) -> str:
        if not v or not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Step id must be alphanumeric/hyphens/underscores: {v}")
        return v


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

class DAG(BaseModel):
    """Directed acyclic graph of steps — the execution plan."""
    name: str
    description: str = ""
    steps: list[Step]

    @model_validator(mode="after")
    def validate_dag(self) -> "DAG":
        ids = {s.id for s in self.steps}

        # Check for duplicate IDs
        if len(ids) != len(self.steps):
            seen = set()
            for s in self.steps:
                if s.id in seen:
                    raise ValueError(f"Duplicate step id: {s.id}")
                seen.add(s.id)

        # Check deps reference valid steps
        for s in self.steps:
            for dep in s.depends_on:
                if dep not in ids:
                    raise ValueError(
                        f"Step '{s.id}' depends on '{dep}' which does not exist"
                    )
            if s.id in s.depends_on:
                raise ValueError(f"Step '{s.id}' depends on itself")

        # Check for cycles via topological sort
        _topological_sort(self.steps)

        return self


# ---------------------------------------------------------------------------
# Execution result (returned by executor)
# ---------------------------------------------------------------------------

class ExecutionResult(BaseModel):
    """Result of executing a single step."""
    status: str = "succeeded"  # succeeded | failed | timeout
    output: str = ""
    error: Optional[str] = None
    exit_code: Optional[int] = None
    artifacts: dict[str, str] = {}
    started_at: datetime = datetime.now(timezone.utc)
    completed_at: datetime = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Check result
# ---------------------------------------------------------------------------

class CheckResult(BaseModel):
    """Result of evaluating a single check."""
    check_type: str
    description: str
    passed: bool
    evidence: str = ""
    verification_strength: str = "deterministic"


# ---------------------------------------------------------------------------
# Audit entry — hash-chained for tamper detection
# ---------------------------------------------------------------------------

class AuditEntry(BaseModel):
    """Immutable record of a single step's execution."""
    step_id: str
    attempt: int = 1
    status: StepStatus
    started_at: str
    completed_at: str
    precheck_results: list[CheckResult] = []
    postcheck_results: list[CheckResult] = []
    execution_output: str = ""
    error: Optional[str] = None
    previous_hash: Optional[str] = None
    entry_hash: str = ""

    def compute_hash(self) -> str:
        data = self.model_dump(exclude={"entry_hash"})
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Execution report — the full audit trail
# ---------------------------------------------------------------------------

class ExecutionReport(BaseModel):
    """Complete audit trail for a pipeline run."""
    dag_name: str
    started_at: str
    completed_at: str
    overall_status: str  # passed | failed | partial
    entries: list[AuditEntry]
    steps_total: int
    steps_passed: int
    steps_failed: int
    steps_blocked: int = 0
    steps_skipped: int = 0
    determinism_hash: str = ""

    def summary_table(self) -> str:
        lines = [
            f"{'Step':<25} {'Status':<20} {'Checks':<15} {'Evidence'}",
            "-" * 80,
        ]
        for e in self.entries:
            pre_ok = sum(1 for c in e.precheck_results if c.passed)
            post_ok = sum(1 for c in e.postcheck_results if c.passed)
            pre_total = len(e.precheck_results)
            post_total = len(e.postcheck_results)
            checks = f"pre:{pre_ok}/{pre_total} post:{post_ok}/{post_total}"

            evidence_parts = []
            for c in e.postcheck_results:
                if c.evidence:
                    evidence_parts.append(c.evidence[:40])
            evidence = "; ".join(evidence_parts) if evidence_parts else "-"

            lines.append(f"{e.step_id:<25} {e.status.value:<20} {checks:<15} {evidence}")

        lines.append("-" * 80)
        lines.append(
            f"Total: {self.steps_total} | "
            f"✅ {self.steps_passed} | "
            f"❌ {self.steps_failed} | "
            f"🚫 {self.steps_blocked} | "
            f"⏭️ {self.steps_skipped}"
        )
        lines.append(f"Determinism hash: {self.determinism_hash}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _topological_sort(steps: list[Step]) -> list[Step]:
    """Kahn's algorithm — raises ValueError on cycles."""
    graph: dict[str, list[str]] = {s.id: list(s.depends_on) for s in steps}
    in_degree: dict[str, int] = {s.id: 0 for s in steps}
    for s in steps:
        for dep in s.depends_on:
            in_degree[s.id] += 1  # noqa: this is intentional

    # Reverse adjacency for traversal
    reverse: dict[str, list[str]] = {s.id: [] for s in steps}
    for s in steps:
        for dep in s.depends_on:
            reverse[dep].append(s.id)

    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    result_ids: list[str] = []

    while queue:
        queue.sort()  # deterministic ordering
        node = queue.pop(0)
        result_ids.append(node)
        for neighbor in reverse[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result_ids) != len(steps):
        raise ValueError("DAG contains a cycle")

    step_map = {s.id: s for s in steps}
    return [step_map[sid] for sid in result_ids]
