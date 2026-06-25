"""CLI for the AI Pipeline Executor.

Usage:
  pipeline run <plan.yaml>       Run a pipeline (shell executor)
  pipeline verify <plan.yaml>    Verify postconditions from a plan
  pipeline show <plan.yaml>      Show the plan as a workflow diagram
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline.checks import CheckEvaluator
from pipeline.engine import PipelineEngine
from pipeline.loader import load_dag
from pipeline.models import (
    AuditEntry,
    DAG,
    ExecutionResult,
    Step,
    StepStatus,
)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
MAGENTA = "\033[95m"


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
            error=f"Timed out after {step.timeout_seconds}s",
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


def on_step_complete(entry: AuditEntry):
    """Print step status as it completes."""
    icons = {
        "completed": f"{GREEN}✅{RESET}",
        "failed": f"{RED}❌{RESET}",
        "precheck_failed": f"{RED}⚠️{RESET}",
        "postcheck_failed": f"{RED}⚠️{RESET}",
        "blocked": f"{YELLOW}🚫{RESET}",
        "skipped": f"{YELLOW}⏭️{RESET}",
        "timeout": f"{RED}⏰{RESET}",
    }
    icon = icons.get(entry.status.value, "❓")
    print(f"  {icon} {entry.step_id}: {entry.status.value}")

    for check in entry.precheck_results:
        status = f"{GREEN}✅{RESET}" if check.passed else f"{RED}❌{RESET}"
        print(f"      pre: {status} {check.description} {DIM}({check.evidence}){RESET}")

    for check in entry.postcheck_results:
        status = f"{GREEN}✅{RESET}" if check.passed else f"{RED}❌{RESET}"
        print(f"      post: {status} {check.description} {DIM}({check.evidence}){RESET}")


def cmd_run(args):
    """Run a pipeline from a YAML file."""
    dag = load_dag(args.plan)

    print(f"\n{BOLD}{CYAN}🔄 Pipeline: {dag.name}{RESET}")
    print(f"   {DIM}Steps: {len(dag.steps)}{RESET}\n")

    engine = PipelineEngine(
        dag=dag,
        executor=shell_executor,
        checker=CheckEvaluator(cwd=args.cwd or os.getcwd()),
        on_step_complete=on_step_complete,
    )

    try:
        report = engine.run()
    except Exception as e:
        print(f"\n{RED}❌ Pipeline stopped: {e}{RESET}")
        report = engine._build_report("", "")

    print(f"\n{report.summary_table()}")

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\n{DIM}Report saved to: {args.output}{RESET}")

    return 0 if report.overall_status == "passed" else 1


def cmd_verify(args):
    """Verify postconditions from a plan without executing anything."""
    dag = load_dag(args.plan)
    checker = CheckEvaluator(cwd=args.cwd or os.getcwd())

    # Filter to single step if --step is provided
    if args.step:
        steps = [s for s in dag.steps if s.id == args.step]
        if not steps:
            print(f"{RED}Error: step '{args.step}' not found in plan{RESET}")
            print(f"Available steps: {', '.join(s.id for s in dag.steps)}")
            return 1
        label = f"step [{args.step}]"
    else:
        steps = dag.steps
        label = f"{len(steps)} steps"

    print(f"\n{BOLD}{CYAN}🔍 Verifying: {dag.name}{RESET}")
    print(f"   {DIM}{label} — checking postconditions only{RESET}\n")

    all_passed = True
    results_summary = []

    for step in steps:
        step_passed = True
        skipped_checks = 0

        # Check preconditions
        pre_results = checker.evaluate(step.prechecks)
        for r in pre_results:
            if r.verification_strength == "skipped":
                icon = f"{YELLOW}⏭️{RESET}"
                skipped_checks += 1
            elif r.passed:
                icon = f"{GREEN}✅{RESET}"
            else:
                icon = f"{RED}❌{RESET}"
                step_passed = False
            print(f"  {icon} [{step.id}] pre: {r.description} {DIM}({r.evidence}){RESET}")

        # Check postconditions
        post_results = checker.evaluate(step.postchecks)
        for r in post_results:
            if r.verification_strength == "skipped":
                icon = f"{YELLOW}⏭️{RESET}"
                skipped_checks += 1
            elif r.passed:
                icon = f"{GREEN}✅{RESET}"
            else:
                icon = f"{RED}❌{RESET}"
                step_passed = False
            print(f"  {icon} [{step.id}] post: {r.description} {DIM}({r.evidence}){RESET}")

        if not step_passed:
            all_passed = False

        results_summary.append((step.id, step_passed))

    # Summary
    passed_count = sum(1 for _, p in results_summary if p)
    total = len(results_summary)
    total = len(results_summary)
    print(f"\n{'─' * 50}")

    for sid, passed in results_summary:
        icon = f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"
        print(f"  {icon} {sid}")

    print(f"{'─' * 50}")
    color = GREEN if all_passed else RED
    print(f"  {BOLD}Verification: {color}{'PASSED' if all_passed else 'FAILED'}{RESET} ({passed_count}/{total})")

    if args.output:
        report = {
            "plan": args.plan,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "status": "passed" if all_passed else "failed",
            "steps": [{"id": sid, "passed": p} for sid, p in results_summary],
        }
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  {DIM}Report saved to: {args.output}{RESET}")

    return 0 if all_passed else 1


def cmd_show(args):
    """Display a plan as a workflow diagram."""
    dag = load_dag(args.plan)

    print(f"\n{BOLD}{MAGENTA}═══ PIPELINE PLAN ═══{RESET}")
    print(f"  {BOLD}Name:{RESET} {dag.name}")
    if dag.description:
        print(f"  {BOLD}Desc:{RESET} {dag.description}")
    print(f"  {BOLD}Steps:{RESET} {len(dag.steps)}")
    print()

    for i, step in enumerate(dag.steps, 1):
        deps = ", ".join(step.depends_on) if step.depends_on else "none"
        pre_count = len(step.prechecks)
        post_count = len(step.postchecks)

        print(f"  {BOLD}{i}.{RESET} [{CYAN}{step.id}{RESET}] — {step.description}")
        print(f"     {DIM}Action: {step.action}{RESET}")
        print(f"     {DIM}Depends: {deps} | Pre: {pre_count} checks | Post: {post_count} checks{RESET}")

        if step.failure_policy.on_precheck_failure == "skip":
            print(f"     {YELLOW}(optional){RESET}")
        print()

    print(f"{BOLD}{MAGENTA}═══════════════════{RESET}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="AI Pipeline Executor — deterministic step-by-step execution with verification",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    p_run = subparsers.add_parser("run", help="Execute a pipeline from YAML")
    p_run.add_argument("plan", help="Path to pipeline YAML file")
    p_run.add_argument("--cwd", help="Working directory for checks", default=None)
    p_run.add_argument("--output", "-o", help="Save report as JSON", default=None)

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify postconditions only (no execution)")
    p_verify.add_argument("plan", help="Path to pipeline YAML file")
    p_verify.add_argument("--step", help="Verify a single step by ID (instead of all)", default=None)
    p_verify.add_argument("--cwd", help="Working directory for checks", default=None)
    p_verify.add_argument("--output", "-o", help="Save report as JSON", default=None)

    # show
    p_show = subparsers.add_parser("show", help="Display pipeline plan")
    p_show.add_argument("plan", help="Path to pipeline YAML file")

    args = parser.parse_args()

    if args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    elif args.command == "show":
        sys.exit(cmd_show(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
