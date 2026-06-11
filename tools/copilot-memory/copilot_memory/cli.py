"""CLI for Copilot Memory — safety-net for complex operations.

Simple operations (read/list/add rules) are handled by the AI inline.
This tool handles: verify, compact, init, repair, export, status.

Usage:
  copilot-memory status              Show project memory health
  copilot-memory verify [--fix]      Check integrity, optionally repair
  copilot-memory compact             Enforce storage caps, prune stale data
  copilot-memory init                Create project memory for current dir
  copilot-memory export [team]       Export rules for team sharing
  copilot-memory schema-fix          Add schema_version to all YAML files
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from copilot_memory.models import (
    ContextFile,
    LatestSession,
    Rule,
    RulesFile,
    SessionEntry,
    VerifyReport,
    FileCheck,
    now_iso,
)
from copilot_memory.store import (
    EXPECTED_FILES,
    GLOBAL_DIR,
    MEMORY_ROOT,
    TEMPLATE_DIR,
    check_session_integrity,
    ensure_project_dir,
    find_project_dir,
    get_dir_size,
    list_sessions,
    load_context,
    load_latest_session,
    load_prefs,
    load_rules,
    save_rules,
    save_context,
    save_prefs,
    save_latest_session,
    _read_yaml,
    _write_yaml,
    _read_json,
    _write_json,
)


# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _no_color() -> bool:
    return os.environ.get("NO_COLOR") is not None or not sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _no_color():
        return text
    return f"{code}{text}{RESET}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    """Show project memory health overview."""
    project_dir = find_project_dir(args.cwd)

    # Global stats
    global_rules = load_rules(GLOBAL_DIR) if GLOBAL_DIR.exists() else RulesFile()
    global_prefs = load_prefs(GLOBAL_DIR) if GLOBAL_DIR.exists() else {}
    global_pref_count = len([k for k in global_prefs if k != "schema_version"])

    print(f"\n{_c(BOLD + CYAN, '🧠 Copilot Project Memory — Status')}")
    print(f"{'─' * 45}")

    print(f"\n{_c(BOLD, '🌍 Global:')}")
    print(f"  Rules: {len(global_rules.rules)}")
    print(f"  Preferences: {global_pref_count}")

    if not project_dir:
        print(f"\n{_c(YELLOW, '⚠️  No project memory found for this directory.')}")
        print(f"  Run: {_c(CYAN, 'copilot-memory init')} to create one.\n")
        return 0

    # Project stats
    rules = load_rules(project_dir)
    prefs = load_prefs(project_dir)
    pref_count = len([k for k in prefs if k != "schema_version"])
    context = load_context(project_dir)
    sessions = list_sessions(project_dir)
    latest = load_latest_session(project_dir)
    dangling, mismatched = check_session_integrity(project_dir)
    total_size = get_dir_size(project_dir)

    print(f"\n{_c(BOLD, f'📂 Project: {context.name or project_dir.name}')}")
    print(f"  Rules: {len(rules.rules)}")
    print(f"  Preferences: {pref_count}")
    print(f"  Sessions: {len(sessions)}")
    if context.stack:
        print(f"  Stack: {', '.join(context.stack)}")
    print(f"  Size: {total_size / 1024:.1f} KB")

    # Health indicators
    print(f"\n{_c(BOLD, '🏥 Health:')}")
    issues = 0

    # Check for missing files
    for fname in EXPECTED_FILES:
        fpath = project_dir / fname
        if not fpath.exists():
            print(f"  {_c(YELLOW, '⚠️')} Missing: {fname}")
            issues += 1

    # Check schema versions
    for fname in EXPECTED_FILES:
        fpath = project_dir / fname
        if fpath.exists():
            data = _read_yaml(fpath)
            if "schema_version" not in data:
                print(f"  {_c(YELLOW, '⚠️')} No schema_version: {fname}")
                issues += 1

    # Check session integrity
    for d in dangling:
        print(f"  {_c(RED, '❌')} Dangling: {d}")
        issues += 1
    for m in mismatched:
        print(f"  {_c(RED, '❌')} Mismatch: {m}")
        issues += 1

    if issues == 0:
        print(f"  {_c(GREEN, '✅ All checks passed')}")
    else:
        print(f"\n  {_c(YELLOW, f'⚠️  {issues} issue(s) found.')} Run: copilot-memory verify --fix")

    # Last session
    if latest and sessions:
        last = sessions[0][1]
        print(f"\n{_c(BOLD, '📝 Last session:')}")
        print(f"  {last.summary or '(no summary)'}")
        print(f"  Status: {last.status} | Updated: {last.lastUpdatedAt[:10] if last.lastUpdatedAt else 'unknown'}")
        if latest.activeSession:
            print(f"  📌 Active named session: {latest.activeSession}")

    print()
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Check integrity of all memory files, optionally repair."""
    project_dir = find_project_dir(args.cwd)
    if not project_dir:
        print(f"{_c(RED, '❌ No project memory found.')} Run: copilot-memory init")
        return 1

    report = VerifyReport(project=project_dir.name)
    fix = args.fix

    print(f"\n{_c(BOLD + CYAN, '🔍 Memory Integrity Check')}")
    print(f"  Project: {project_dir.name}")
    print(f"  Mode: {'fix' if fix else 'check only'}\n")

    # 1. Check expected files
    for fname in EXPECTED_FILES:
        fpath = project_dir / fname
        if not fpath.exists():
            if fix:
                # Recreate from template
                template = TEMPLATE_DIR / fname
                if template.exists():
                    data = _read_yaml(template)
                    data["schema_version"] = 1
                    _write_yaml(fpath, data)
                    status = "recreated"
                    detail = f"Recreated from template"
                else:
                    _write_yaml(fpath, {"schema_version": 1})
                    status = "recreated"
                    detail = "Created empty with schema_version"
                print(f"  {_c(YELLOW, '⚠️')} {fname} — {detail}")
            else:
                status = "missing"
                detail = "File not found"
                print(f"  {_c(RED, '❌')} {fname} — missing")
        else:
            # Validate content
            data = _read_yaml(fpath)
            if not data:
                status = "malformed"
                detail = "Empty or invalid YAML"
                print(f"  {_c(RED, '❌')} {fname} — {detail}")
            elif "schema_version" not in data:
                if fix:
                    data["schema_version"] = 1
                    _write_yaml(fpath, data)
                    status = "ok"
                    detail = "Added schema_version"
                    print(f"  {_c(GREEN, '✅')} {fname} (fixed: added schema_version)")
                else:
                    status = "ok"
                    detail = "Missing schema_version"
                    print(f"  {_c(YELLOW, '⚠️')} {fname} — no schema_version")
            else:
                status = "ok"
                detail = f"Valid (schema v{data['schema_version']})"
                print(f"  {_c(GREEN, '✅')} {fname} ({detail})")

            # Validate rules.yml specifically
            if fname == "rules.yml" and status == "ok":
                try:
                    load_rules(project_dir)
                except Exception as e:
                    detail = f"Validation error: {e}"
                    status = "malformed"
                    print(f"  {_c(RED, '   ↳ ❌')} {detail}")

        report.checks.append(FileCheck(path=fname, status=status, detail=detail))

    # 2. Check sessions
    print()
    dangling, mismatched = check_session_integrity(project_dir)
    report.dangling_sessions = dangling
    report.mismatched_ids = mismatched

    if dangling:
        for d in dangling:
            print(f"  {_c(RED, '❌')} Dangling session: {d}")
        if fix:
            # Clear latest.json to remove dangling pointer
            latest_path = project_dir / "sessions" / "latest.json"
            if latest_path.exists():
                _write_json(latest_path, {
                    "lastSessionId": "",
                    "lastUpdatedAt": now_iso(),
                    "activeSession": None,
                })
                print(f"  {_c(GREEN, '  ↳ ✅')} Reset latest.json")

    if mismatched:
        for m in mismatched:
            print(f"  {_c(RED, '❌')} ID mismatch: {m}")
        if fix:
            # Rename files to match their sessionId
            sessions_dir = project_dir / "sessions"
            for path in sessions_dir.rglob("*.json"):
                if path.name == "latest.json":
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    sid = data.get("sessionId", "")
                    if sid and sid != path.stem:
                        new_path = path.parent / f"{sid}.json"
                        if not new_path.exists():
                            path.rename(new_path)
                            print(f"  {_c(GREEN, '  ↳ ✅')} Renamed {path.name} → {sid}.json")
                except Exception:
                    continue

    if not dangling and not mismatched:
        print(f"  {_c(GREEN, '✅')} Sessions: no integrity issues")

    # 3. Summary
    report.total_size_bytes = get_dir_size(project_dir)
    errors = sum(1 for c in report.checks if c.status in ("missing", "malformed"))
    errors += len(dangling) + len(mismatched)

    print(f"\n{'─' * 45}")
    if errors == 0:
        print(f"  {_c(GREEN + BOLD, '✅ All checks passed')}")
    elif fix:
        print(f"  {_c(YELLOW + BOLD, f'⚠️  {errors} issue(s) found and repaired')}")
    else:
        print(f"  {_c(RED + BOLD, f'❌ {errors} issue(s) found')} — run with --fix to repair")

    print(f"  📦 Total memory size: {report.total_size_bytes / 1024:.1f} KB\n")
    return 0 if errors == 0 else 1


def cmd_compact(args: argparse.Namespace) -> int:
    """Enforce storage caps and prune stale data."""
    project_dir = find_project_dir(args.cwd)
    if not project_dir:
        print(f"{_c(RED, '❌ No project memory found.')}")
        return 1

    print(f"\n{_c(BOLD + CYAN, '📊 Compact: Enforcing storage caps')}\n")
    actions = 0

    # 1. Cap default sessions at 10
    default_dir = project_dir / "sessions" / "_default"
    if default_dir.exists():
        sessions = sorted(default_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if len(sessions) > 10:
            to_remove = sessions[:len(sessions) - 10]
            for s in to_remove:
                s.unlink()
                print(f"  {_c(GREEN, '✅')} Pruned old session: {s.name}")
                actions += 1

    # 2. Cap named session entries at 20 each
    sessions_dir = project_dir / "sessions"
    if sessions_dir.exists():
        for subdir in sessions_dir.iterdir():
            if subdir.is_dir() and subdir.name != "_default":
                entries = sorted(subdir.glob("*.json"), key=lambda p: p.stat().st_mtime)
                if len(entries) > 20:
                    to_remove = entries[:len(entries) - 20]
                    for e in to_remove:
                        e.unlink()
                        print(f"  {_c(GREEN, '✅')} Pruned {subdir.name}/{e.name}")
                        actions += 1

    # 3. Cap tracking hotspots at 5
    tracking_path = project_dir / "tracking.yml"
    if tracking_path.exists():
        data = _read_yaml(tracking_path)
        hotspots = data.get("hotspots", [])
        if isinstance(hotspots, list) and len(hotspots) > 5:
            hotspots.sort(key=lambda h: h.get("touch_count", 0), reverse=True)
            data["hotspots"] = hotspots[:5]
            _write_yaml(tracking_path, data)
            print(f"  {_c(GREEN, '✅')} Pruned hotspots: kept top 5")
            actions += 1

        errors = data.get("common_errors", [])
        if isinstance(errors, list) and len(errors) > 10:
            data["common_errors"] = errors[-10:]
            _write_yaml(tracking_path, data)
            print(f"  {_c(GREEN, '✅')} Pruned common_errors: kept latest 10")
            actions += 1

    # 4. Report stale rules (never auto-delete)
    rules = load_rules(project_dir)
    stale_rules = []
    now = datetime.now(timezone.utc)
    for rule in rules.rules:
        if rule.last_used:
            try:
                last = datetime.fromisoformat(rule.last_used.replace("Z", "+00:00"))
                days = (now - last).days
                if days > 30:
                    stale_rules.append((rule.id, days))
            except (ValueError, TypeError):
                pass

    if stale_rules:
        print(f"\n  {_c(YELLOW, '💡 Possibly stale rules (not used in 30+ days):')}")
        for rule_id, days in stale_rules:
            print(f"    - [{rule_id}] last used: {days} days ago")
        print(f"\n  Use :forget <id> to remove, or :rules touch <id> to keep.")

    if actions == 0 and not stale_rules:
        print(f"  {_c(GREEN, '✅ Nothing to compact — all within limits.')}")

    print()
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Create project memory for the current directory."""
    existing = find_project_dir(args.cwd)
    if existing:
        print(f"{_c(GREEN, '✅ Project memory already exists:')} {existing}")
        return 0

    project_dir = ensure_project_dir(args.cwd)

    # Copy template files
    for fname in EXPECTED_FILES:
        fpath = project_dir / fname
        if not fpath.exists():
            template = TEMPLATE_DIR / fname
            if template.exists():
                data = _read_yaml(template)
            else:
                data = {}
            data["schema_version"] = 1
            _write_yaml(fpath, data)

    # Create sessions directory
    (project_dir / "sessions" / "_default").mkdir(parents=True, exist_ok=True)
    (project_dir / "snippets").mkdir(exist_ok=True)

    # Initialize latest.json
    _write_json(project_dir / "sessions" / "latest.json", {
        "lastSessionId": "",
        "lastUpdatedAt": now_iso(),
        "activeSession": None,
    })

    print(f"\n{_c(GREEN + BOLD, '✅ Project memory created:')}")
    print(f"  📂 {project_dir}")
    print(f"  Files: {', '.join(EXPECTED_FILES)}")
    print(f"  Sessions: sessions/_default/")
    print(f"\n  Type {_c(CYAN, ':status')} in Copilot to load it.\n")
    return 0


def cmd_schema_fix(args: argparse.Namespace) -> int:
    """Add schema_version to all YAML files that are missing it."""
    target = args.cwd or str(MEMORY_ROOT)
    root = Path(target)
    if not root.exists():
        print(f"{_c(RED, '❌ Path not found:')} {root}")
        return 1

    fixed = 0
    for yml_path in root.rglob("*.yml"):
        data = _read_yaml(yml_path)
        if data and "schema_version" not in data:
            data["schema_version"] = 1
            _write_yaml(yml_path, data)
            rel = yml_path.relative_to(root)
            print(f"  {_c(GREEN, '✅')} Added schema_version: {rel}")
            fixed += 1

    if fixed == 0:
        print(f"{_c(GREEN, '✅ All YAML files already have schema_version.')}")
    else:
        print(f"\n{_c(GREEN, f'✅ Fixed {fixed} file(s).')}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export project memory for team sharing."""
    project_dir = find_project_dir(args.cwd)
    if not project_dir:
        print(f"{_c(RED, '❌ No project memory found.')}")
        return 1

    context = load_context(project_dir)
    rules = load_rules(project_dir)
    prefs = load_prefs(project_dir)

    lines = [
        "<!-- Auto-exported by copilot-project-memory. Do not edit manually. -->",
        "",
        f"# {context.name or 'Project'} — Copilot Instructions",
        "",
    ]

    # Context
    if context.description:
        lines.append(f"## Project\n{context.description}\n")
    if context.stack:
        lines.append(f"## Tech Stack\n{', '.join(context.stack)}\n")
    if context.key_files:
        lines.append("## Key Files")
        for f in context.key_files:
            lines.append(f"- `{f}`")
        lines.append("")

    # Rules
    shared_rules = [r for r in rules.rules if r.share]
    if shared_rules:
        donts = [r for r in shared_rules if r.type == "dont"]
        dos = [r for r in shared_rules if r.type == "do"]

        if donts:
            lines.append("## Don'ts")
            for r in donts:
                lines.append(f"- {r.description}")
            lines.append("")

        if dos:
            lines.append("## Do's")
            for r in dos:
                lines.append(f"- {r.description}")
            lines.append("")

    output = "\n".join(lines)

    if args.target == "team":
        # Write to .github/copilot-instructions.md
        work_dir = args.cwd or os.getcwd()
        git_root = None
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, cwd=work_dir,
            )
            if result.returncode == 0:
                git_root = result.stdout.strip()
        except Exception:
            pass

        if git_root:
            out_dir = Path(git_root) / ".github"
            out_dir.mkdir(exist_ok=True)
            out_path = out_dir / "copilot-instructions.md"
            out_path.write_text(output, encoding="utf-8")
            print(f"{_c(GREEN, '✅ Exported to:')} {out_path}")
        else:
            print(output)
    else:
        print(output)

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _add_cwd(p: argparse.ArgumentParser) -> None:
    """Add --cwd flag to a subparser."""
    p.add_argument("--cwd", help="Working directory override", default=None)


def main():
    parser = argparse.ArgumentParser(
        prog="copilot-memory",
        description="Safety-net CLI for Copilot Project Memory — handles complex ops deterministically.",
    )
    parser.add_argument("--version", action="version", version="copilot-memory 0.1.0")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # status
    p_status = sub.add_parser("status", help="Show project memory health overview")
    _add_cwd(p_status)

    # verify
    p_verify = sub.add_parser("verify", help="Check integrity of memory files")
    p_verify.add_argument("--fix", action="store_true", help="Attempt to repair issues")
    _add_cwd(p_verify)

    # compact
    p_compact = sub.add_parser("compact", help="Enforce storage caps and prune stale data")
    _add_cwd(p_compact)

    # init
    p_init = sub.add_parser("init", help="Create project memory for current directory")
    _add_cwd(p_init)

    # schema-fix
    p_schema = sub.add_parser("schema-fix", help="Add schema_version to all YAML files")
    _add_cwd(p_schema)

    # export
    p_export = sub.add_parser("export", help="Export memory for team sharing")
    p_export.add_argument("target", nargs="?", default="stdout",
                          choices=["team", "stdout"],
                          help="Export target (default: stdout)")
    _add_cwd(p_export)

    args = parser.parse_args()

    if args.command == "status":
        sys.exit(cmd_status(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    elif args.command == "compact":
        sys.exit(cmd_compact(args))
    elif args.command == "init":
        sys.exit(cmd_init(args))
    elif args.command == "schema-fix":
        sys.exit(cmd_schema_fix(args))
    elif args.command == "export":
        sys.exit(cmd_export(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
