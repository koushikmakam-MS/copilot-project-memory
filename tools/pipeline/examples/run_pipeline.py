"""Example: Run a pipeline with a shell executor."""

import subprocess
from datetime import datetime, timezone

from pipeline import PipelineEngine, CheckEvaluator, ExecutionResult
from pipeline.loader import load_dag
from pipeline.models import AuditEntry, Step


def shell_executor(step: Step) -> ExecutionResult:
    """Execute a step's action as a shell command."""
    start = datetime.now(timezone.utc)
    try:
        result = subprocess.run(
            step.action,
            shell=True,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
        )
        return ExecutionResult(
            status="succeeded" if result.returncode == 0 else "failed",
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None,
            exit_code=result.returncode,
            started_at=start,
            completed_at=datetime.now(timezone.utc),
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            status="timeout",
            error=f"Command timed out after {step.timeout_seconds}s",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        return ExecutionResult(
            status="failed",
            error=str(e),
            started_at=start,
            completed_at=datetime.now(timezone.utc),
        )


def on_step_done(entry: AuditEntry):
    """Callback: print step status as it completes."""
    icon = {
        "completed": "✅",
        "failed": "❌",
        "precheck_failed": "⚠️",
        "postcheck_failed": "⚠️",
        "blocked": "🚫",
        "skipped": "⏭️",
        "timeout": "⏰",
    }.get(entry.status.value, "❓")
    print(f"  {icon} {entry.step_id}: {entry.status.value}")


def main():
    # Load the DAG from YAML
    dag = load_dag("examples/deploy_service.yaml")

    print(f"🚀 Pipeline: {dag.name}")
    print(f"   Steps: {len(dag.steps)}")
    print()

    # Create engine with shell executor
    engine = PipelineEngine(
        dag=dag,
        executor=shell_executor,
        checker=CheckEvaluator(),
        on_step_complete=on_step_done,
    )

    # Run!
    try:
        report = engine.run()
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        # Still print whatever we have
        report = engine._build_report("", "")

    print()
    print(report.summary_table())


if __name__ == "__main__":
    main()
