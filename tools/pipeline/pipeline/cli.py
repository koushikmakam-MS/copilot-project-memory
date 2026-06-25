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

import yaml

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
    # Approval gate: check if plan has been approved
    plan_path = Path(args.plan)
    with open(plan_path, "r", encoding="utf-8") as f:
        raw_plan = yaml.safe_load(f)

    if isinstance(raw_plan, dict) and "status" in raw_plan:
        status = raw_plan.get("status", "")
        if status == "pending_approval":
            print(f"\n{RED}🚫 BLOCKED: This plan has not been approved yet.{RESET}")
            print(f"   {DIM}Current status: pending_approval{RESET}")
            print(f"\n   Run: {BOLD}pipeline approve {args.plan}{RESET} to approve first")
            print(f"   Run: {BOLD}pipeline show {args.plan}{RESET} to review the plan\n")
            return 1
        elif status == "cancelled":
            print(f"\n{RED}🚫 BLOCKED: This plan was cancelled.{RESET}")
            print(f"   Re-approve with: {BOLD}pipeline approve {args.plan}{RESET}\n")
            return 1

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


def cmd_plan(args):
    """Create a new plan YAML file with pending_approval status."""
    output_path = Path(args.output)

    # If the file already exists, check its status
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f)
        if isinstance(existing, dict) and existing.get("status") == "approved":
            print(f"{RED}Error: Plan already approved. Use 'pipeline run' to execute.{RESET}")
            return 1
        if isinstance(existing, dict) and existing.get("status") == "running":
            print(f"{RED}Error: Plan is currently running. Use 'pipeline show' to check status.{RESET}")
            return 1

    # Generate a skeleton plan
    plan_content = {
        "name": args.name or "Untitled Pipeline",
        "description": args.description or "",
        "status": "pending_approval",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    # If steps are provided via --steps (comma-separated IDs), scaffold them
    if args.steps:
        step_ids = [s.strip() for s in args.steps.split(",")]
        prev_id = None
        for step_id in step_ids:
            step_entry = {
                "id": step_id,
                "do": f"TODO: describe {step_id}",
                "run": f"echo TODO: implement {step_id}",
                "after": [prev_id] if prev_id else [],
                "check": ["exit code 0"],
            }
            plan_content["steps"].append(step_entry)
            prev_id = step_id

    # Write the plan
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(plan_content, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"\n{BOLD}{CYAN}📋 Plan created: {output_path}{RESET}")
    print(f"   {DIM}Status: pending_approval{RESET}")
    print(f"   {DIM}Steps: {len(plan_content['steps'])}{RESET}")
    print(f"\n{YELLOW}⏳ This plan requires approval before execution.{RESET}")
    print(f"   Run: {BOLD}pipeline approve {output_path}{RESET} to approve")
    print(f"   Run: {BOLD}pipeline show {output_path}{RESET} to review")
    print(f"   Run: {BOLD}pipeline run {output_path}{RESET} after approval\n")
    return 0


def cmd_approve(args):
    """Approve a pending plan, unlocking it for execution."""
    plan_path = Path(args.plan)

    if not plan_path.exists():
        print(f"{RED}Error: Plan file not found: {plan_path}{RESET}")
        return 1

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = yaml.safe_load(f)

    if not isinstance(plan, dict):
        print(f"{RED}Error: Invalid plan file format{RESET}")
        return 1

    current_status = plan.get("status", "unknown")

    if current_status == "approved":
        print(f"{YELLOW}Plan is already approved.{RESET}")
        return 0

    if current_status == "running":
        print(f"{RED}Error: Plan is currently running — cannot re-approve.{RESET}")
        return 1

    if current_status == "cancelled":
        print(f"{YELLOW}Warning: Re-approving a previously cancelled plan.{RESET}")

    # Update status to approved
    plan["status"] = "approved"
    plan["approved_at"] = datetime.now(timezone.utc).isoformat()

    with open(plan_path, "w", encoding="utf-8") as f:
        yaml.dump(plan, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    step_count = len(plan.get("steps", []))
    print(f"\n{GREEN}✅ Plan approved: {plan.get('name', plan_path.stem)}{RESET}")
    print(f"   {DIM}Steps: {step_count}{RESET}")
    print(f"   {DIM}Approved at: {plan['approved_at']}{RESET}")
    print(f"\n   Run: {BOLD}pipeline run {plan_path}{RESET} to execute\n")
    return 0


def cmd_status(args):
    """Show the status of a plan file — is it pending, approved, running, or done?"""
    plan_path = Path(args.plan)

    if not plan_path.exists():
        print(f"{RED}Error: Plan file not found: {plan_path}{RESET}")
        return 1

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = yaml.safe_load(f)

    if not isinstance(plan, dict):
        print(f"{RED}Error: Invalid plan file format{RESET}")
        return 1

    status = plan.get("status", "unknown")
    name = plan.get("name", plan_path.stem)
    steps = plan.get("steps", [])

    status_icons = {
        "pending_approval": f"{YELLOW}⏳ PENDING APPROVAL{RESET}",
        "approved": f"{CYAN}✅ APPROVED (not yet run){RESET}",
        "running": f"{CYAN}🔄 RUNNING{RESET}",
        "completed": f"{GREEN}✅ COMPLETED{RESET}",
        "failed": f"{RED}❌ FAILED{RESET}",
        "cancelled": f"{DIM}🚫 CANCELLED{RESET}",
    }

    print(f"\n{BOLD}📋 {name}{RESET}")
    print(f"   Status: {status_icons.get(status, status)}")
    print(f"   Steps:  {len(steps)}")

    if plan.get("created_at"):
        print(f"   Created: {plan['created_at']}")
    if plan.get("approved_at"):
        print(f"   Approved: {plan['approved_at']}")

    # Show per-step status if available
    has_step_status = any(isinstance(s, dict) and "status" in s for s in steps)
    if has_step_status:
        print(f"\n   {'Step':<25} {'Status'}")
        print(f"   {'─' * 45}")
        for s in steps:
            if isinstance(s, dict):
                sid = s.get("id", "?")
                ss = s.get("status", "pending")
                icon = {"completed": "✅", "running": "🔄", "failed": "❌", "pending": "⏳"}.get(ss, "?")
                print(f"   {icon} {sid:<23} {ss}")

    print()
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="AI Pipeline Executor — deterministic step-by-step execution with verification",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # plan (new — creates a plan without executing)
    p_plan = subparsers.add_parser("plan", help="Create a new plan YAML (pending approval)")
    p_plan.add_argument("--output", "-o", help="Output path for the plan YAML", required=True)
    p_plan.add_argument("--name", "-n", help="Pipeline name", default=None)
    p_plan.add_argument("--description", "-d", help="Pipeline description", default=None)
    p_plan.add_argument("--steps", "-s", help="Comma-separated step IDs to scaffold", default=None)

    # approve (new — unlocks a plan for execution)
    p_approve = subparsers.add_parser("approve", help="Approve a pending plan for execution")
    p_approve.add_argument("plan", help="Path to pipeline YAML file")

    # status (new — check plan status)
    p_status = subparsers.add_parser("status", help="Show the status of a plan")
    p_status.add_argument("plan", help="Path to pipeline YAML file")

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

    if args.command == "plan":
        sys.exit(cmd_plan(args))
    elif args.command == "approve":
        sys.exit(cmd_approve(args))
    elif args.command == "status":
        sys.exit(cmd_status(args))
    elif args.command == "run":
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
