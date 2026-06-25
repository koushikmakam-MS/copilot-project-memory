# 🧰 Tool Development Guide

> How to create tools that integrate with Copilot Project Memory.

---

## What is a Tool?

A tool is a **standalone Python CLI package** that lives in `tools/<name>/` and gets auto-installed by the installer. Copilot calls it via shell commands — the user never interacts with it directly.

```
tools/
├── pipeline/          ← verification engine (ships with v1)
├── your-tool/           ← your new tool
│   ├── pyproject.toml   ← REQUIRED: package metadata
│   ├── your_tool/       ← REQUIRED: Python package (same name or different)
│   │   ├── __init__.py
│   │   └── cli.py       ← REQUIRED: CLI entry point
│   ├── tests/           ← REQUIRED: test suite
│   │   └── test_*.py
│   ├── README.md        ← RECOMMENDED: tool documentation
│   └── examples/        ← OPTIONAL: example configs/usage
```

---

## Requirements

### Must Have

| # | Requirement | Why |
|---|-------------|-----|
| 1 | `pyproject.toml` with `[project.scripts]` entry | Installer discovers tools by `pyproject.toml` presence, scripts make it callable |
| 2 | CLI entry point (`tool-name --help` works) | Copilot calls tools via shell — no Python API |
| 3 | `--help` on every command and subcommand | Copilot reads help text to understand usage |
| 4 | Exit code 0 = success, non-zero = failure | Copilot checks exit codes to determine pass/fail |
| 5 | UTF-8 stdout output (no binary) | Copilot reads stdout to show results |
| 6 | Works on Windows + macOS + Linux | Installer runs cross-platform |
| 7 | Python 3.10+ compatibility | Minimum supported version |
| 8 | Tests (`tests/test_*.py`) with pytest | Verify tool works before shipping |
| 9 | No interactive prompts (stdin) | Copilot can't type into prompts — all input via args/flags |
| 10 | Idempotent operations where possible | Safe to re-run without side effects |

### Should Have

| # | Requirement | Why |
|---|-------------|-----|
| 1 | `--output` / `-o` flag for JSON output | Machine-readable results for Copilot to parse |
| 2 | `--quiet` flag to suppress decorative output | Cleaner output when called programmatically |
| 3 | `--cwd` flag to set working directory | Tools may run from a different directory than the project |
| 4 | Colored terminal output (ANSI) with graceful fallback | Nice UX when user sees output, but don't break pipes |
| 5 | `README.md` in tool directory | Documents what the tool does and how to use it |
| 6 | Windows UTF-8 handling (`sys.stdout.reconfigure`) | Prevents encoding crashes on Windows |

### Must Not

| # | Rule | Why |
|---|------|-----|
| 1 | No network calls without explicit opt-in flag | Tools run in user's environment — no surprise traffic |
| 2 | No file writes outside `--cwd` or explicit output path | Don't pollute the user's filesystem |
| 3 | No secrets/credentials in source | Tools are open source in the repo |
| 4 | No heavy dependencies (keep install < 30s) | Installer runs pip install for each tool |
| 5 | No GUI or browser opens | CLI-only environment |

---

## pyproject.toml Template

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "your-tool-name"
version = "0.1.0"
description = "One-line description of what this tool does"
requires-python = ">=3.10"
dependencies = [
    # Keep minimal — each dep adds install time
    # "pydantic>=2.0",
    # "pyyaml>=6.0",
]

[project.scripts]
your-tool-name = "your_tool.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]
```

**Key rules:**
- `[project.scripts]` is mandatory — this creates the CLI command
- Package name in `[project.scripts]` becomes the command Copilot calls
- Keep dependencies minimal — every dep adds to install time
- Use `setuptools.build_meta` as build backend (compatible everywhere)

---

## CLI Structure

### Single-command tool
```python
"""Simple tool with one action."""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        prog="my-tool",
        description="What this tool does",
    )
    parser.add_argument("input", help="Input file or value")
    parser.add_argument("--cwd", help="Working directory", default=None)
    parser.add_argument("--output", "-o", help="Save result as JSON", default=None)
    parser.add_argument("--quiet", help="Suppress decorative output", action="store_true")
    
    args = parser.parse_args()
    
    # Do work...
    success = do_the_thing(args.input)
    
    # Exit code signals pass/fail to Copilot
    sys.exit(0 if success else 1)
```

### Multi-command tool (subcommands)
```python
"""Tool with multiple subcommands."""
import argparse
import sys

def cmd_check(args):
    """Check something."""
    # ...
    return 0  # exit code

def cmd_fix(args):
    """Fix something."""
    # ...
    return 0

def main():
    parser = argparse.ArgumentParser(prog="my-tool")
    subparsers = parser.add_subparsers(dest="command")
    
    p_check = subparsers.add_parser("check", help="Check something")
    p_check.add_argument("target")
    
    p_fix = subparsers.add_parser("fix", help="Fix something")
    p_fix.add_argument("target")
    
    args = parser.parse_args()
    
    commands = {"check": cmd_check, "fix": cmd_fix}
    if args.command in commands:
        sys.exit(commands[args.command](args))
    else:
        parser.print_help()
        sys.exit(0)
```

---

## Output Format

### Human-readable (default)

```
🔍 Checking: my-project
  ✅ config.yaml is valid
  ❌ missing required field: "version"
  Verification: FAILED (1/2)
```

### Machine-readable (--output / -o)

```json
{
  "tool": "my-tool",
  "command": "check",
  "status": "failed",
  "results": [
    {"id": "config-valid", "passed": true, "evidence": "YAML parses correctly"},
    {"id": "version-field", "passed": false, "evidence": "field 'version' not found"}
  ]
}
```

**Rules:**
- JSON output goes to the file specified by `--output`, not stdout
- stdout always gets human-readable output (Copilot shows this to the user)
- JSON must be parseable — no ANSI codes, no decorative text

---

## Windows Compatibility

Always add this at the top of your CLI module:

```python
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

And use `Path` objects (not string concatenation) for file paths:
```python
from pathlib import Path

# Good
config_path = Path(args.cwd) / "config.yaml"

# Bad
config_path = args.cwd + "/config.yaml"
```

---

## Hooking Into copilot-instructions.md

This is the most important part. A tool that Copilot doesn't know about will never be called. You need to tell Copilot **three things**:

1. **WHEN** — what triggers the tool (conditions, keywords, phases)
2. **HOW** — the exact shell command to run
3. **WHAT TO DO** — how to interpret results and what action to take

### Integration Patterns

There are 4 patterns for how a tool can integrate:

#### Pattern 1: Per-Step Hook (inline in a workflow)

The tool runs **as part of an existing workflow step**. This is the strongest pattern — hardest for AI to skip because it's embedded in the step template.

**Example:** `pipeline verify --step` runs after every pipeline step.

```markdown
<!-- In the Phase 2: EXECUTE section of copilot-instructions.md -->

For EACH step in the stored plan, output this EXACT structure:

  🔨 EXECUTE:
    <do the actual work>

  📋 POST-CHECK:
    <your own checks>

  🔍 VERIFY (run this shell command — mandatory):
    your-tool check <target> --cwd .
    → Show the output. If exit code ≠ 0, STOP and fix before next step.
```

**Why this works:** The tool call is inside the step template that AI copies for every step. It's not a separate phase that can be forgotten.

**Use this when:** Your tool validates work that was just done (linters, verifiers, security scanners).

#### Pattern 2: Phase Hook (runs at a specific phase)

The tool runs **at a defined point in the pipeline** — after all steps, before reporting, etc.

**Example:** A security scanner that runs after all code is written.

```markdown
#### Phase 3b: SECURITY SCAN (after report, before validation)

Run the security scanner against all modified files:

\```
security-scan check --cwd . --output scan-report.json
\```

- If exit code 0 → proceed to Phase 4
- If exit code 1 → show findings to user, fix critical issues, re-scan
- Include scan results in the pipeline report
```

**Use this when:** Your tool needs to see the complete result, not individual steps.

#### Pattern 3: Trigger-Based (runs when conditions are met)

The tool runs **when specific keywords or conditions appear** in the user's request.

**Example:** A dependency auditor that runs when the user mentions "install", "add package", "update deps".

```markdown
### Tool: dep-audit

**Auto-trigger when:** The user's message contains any of:
`install` · `add package` · `update deps` · `upgrade` · `npm install` · `pip install`

**How to call:**
After the install command completes, run:
\```
dep-audit check --cwd . --lockfile package-lock.json
\```

**Action on result:**
- Exit 0 → continue silently
- Exit 1 → show vulnerabilities to user, ask if they want to fix
```

**Use this when:** Your tool applies to specific types of tasks, not all tasks.

#### Pattern 4: Command-Based (user explicitly invokes)

The tool runs **when the user types a specific command**.

**Example:** A code metrics tool invoked with `:metrics`.

```markdown
### :metrics Command

When the user types `:metrics` or `:metrics <path>`:

1. Run: `code-metrics analyze --cwd . --path <path or "src/">`
2. Show the output to the user
3. If `--output` flag is supported, save to `pipelines/metrics-<timestamp>.json`
```

**Use this when:** The tool is informational/optional, not part of a mandatory workflow.

---

### Instruction Template

Use this template when adding your tool to `copilot-instructions.md`:

```markdown
### Tool: <tool-name>

**Purpose:** One sentence — what does this tool do?

**Installed by:** copilot-project-memory installer (tools/<tool-name>/)

**When to call:**
- [ ] Per-step: after every pipeline step (Pattern 1)
- [ ] Phase hook: at Phase <N> (Pattern 2)  
- [ ] Trigger: when user message contains <keywords> (Pattern 3)
- [ ] Command: when user types :<command> (Pattern 4)

**Trigger conditions:**
<Describe EXACTLY when Copilot should call this tool.
Be specific — vague triggers get ignored.>

**Shell command:**
\```
tool-name <subcommand> <args> --cwd .
\```

**Interpreting results:**
| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | Passed | Continue to next step/phase |
| 1 | Failed | Show output, fix issues, re-run |
| 2 | Warning | Show output, continue (non-blocking) |

**Output format:**
<Describe what stdout looks like so Copilot knows what to show the user>

**Failure handling:**
<What should Copilot do if the tool itself crashes or isn't installed?>
- If tool not found: warn user, continue without verification
- If tool crashes: show error, continue without verification
```

---

### Where to Place Instructions

Position in `copilot-instructions.md` matters — LLMs weight earlier instructions more heavily.

```
copilot-instructions.md layout:
┌─────────────────────────────────────────┐
│ Phase 0: TASK CLASSIFICATION            │  ← Highest priority
│   (tool triggers go here if they're     │
│    per-step or auto-trigger)            │
├─────────────────────────────────────────┤
│ Project Memory System                   │
│   (existing memory features)            │
├─────────────────────────────────────────┤
│ Pipeline Executor Protocol              │
│   Phase 1: DECOMPOSE                    │
│   Phase 1b: STORE & APPROVE            │
│   Phase 2: EXECUTE                      │
│     └─ Per-step tool hooks (Pattern 1)  │  ← Inside the step template
│   Phase 3: REPORT                       │
│     └─ Phase hooks (Pattern 2)          │  ← Between report and validate
│   Phase 4: VALIDATE                     │
├─────────────────────────────────────────┤
│ Tool Reference                          │  ← All tool docs in one section
│   Tool: pipeline                      │
│   Tool: your-tool                       │
│   Tool: another-tool                    │
├─────────────────────────────────────────┤
│ Command Reference                       │
│   :pipeline, :status, :metrics, etc.    │  ← Command-based tools here
└─────────────────────────────────────────┘
```

**Rules of placement:**
1. **Per-step hooks** go INSIDE the Phase 2 step template — not as a separate section
2. **Phase hooks** go between the phases they should run between
3. **Trigger-based** tools go in Phase 0 (task classification) so the trigger check runs early
4. **Command-based** tools go in the Command Reference section at the bottom
5. **Tool reference docs** go in a dedicated "Tool Reference" section — Copilot reads this for `--help` equivalent

---

### Common Mistakes

| Mistake | Why It Fails | Fix |
|---------|-------------|-----|
| "Run tool-name when appropriate" | AI decides "not appropriate" and skips | Specify exact trigger conditions |
| Tool docs at bottom of instructions | AI forgets by the time it reaches execution | Put triggers near Phase 0, hooks inside Phase 2 |
| "You should run..." | "Should" is optional in AI language | "You MUST run..." |
| Only describing what the tool does | AI knows what it does but not when to call it | Focus on WHEN and IF-THEN logic |
| One big paragraph | AI skims paragraphs | Use structured format: trigger → command → action |
| No failure handling | AI panics if tool crashes | Always specify fallback behavior |

---

### Real Example: pipeline Integration

Here's how `pipeline` is integrated — use this as a reference:

**Phase 0 (trigger):**
```markdown
3. Follow ALL phases: 1 → 1b → 2 → **4a (code verify)** → **4b (AI verify)**
```

**Phase 2 (per-step hook — Pattern 1):**
```markdown
🔍 VERIFY (run this shell command — mandatory):
  pipeline verify pipelines/active-plan.yaml --step [step-id] --cwd .
  → Output: ✅ PASS or ❌ FAIL with evidence
```

**Phase 4a (phase hook — Pattern 2):**
```markdown
Run full plan verification:
  pipeline verify pipelines/active-plan.yaml --cwd .
```

**What makes this work:**
1. Trigger is mentioned in Phase 0 → AI plans for it from the start
2. Per-step verify is inside the step template → runs every step
3. Full verify is a phase hook → runs as a final sweep
4. Exit codes drive behavior → 0 = continue, 1 = fix and retry

---

## Testing

### Required tests

```python
# tests/test_cli.py
import subprocess
import sys

def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "your_tool"] + list(args),
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode, result.stdout, result.stderr

class TestCLI:
    def test_help(self):
        code, out, _ = run_cli("--help")
        assert code == 0
        assert "your-tool-name" in out or "usage" in out.lower()

    def test_success_returns_zero(self):
        code, _, _ = run_cli("check", "valid-input")
        assert code == 0

    def test_failure_returns_nonzero(self):
        code, _, _ = run_cli("check", "invalid-input")
        assert code != 0

    def test_json_output(self, tmp_path):
        out_file = tmp_path / "result.json"
        run_cli("check", "input", "-o", str(out_file))
        assert out_file.exists()
        import json
        data = json.loads(out_file.read_text())
        assert "status" in data
```

### Run tests
```bash
cd tools/your-tool
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Checklist: Before Submitting a Tool

- [ ] `pyproject.toml` exists with `[project.scripts]`
- [ ] `tool-name --help` works after `pip install`
- [ ] Exit code 0 on success, non-zero on failure
- [ ] No interactive stdin prompts
- [ ] Works on Windows (tested or CI)
- [ ] Tests exist and pass (`pytest tests/`)
- [ ] `--cwd` flag supported (if tool reads files)
- [ ] UTF-8 output handling for Windows
- [ ] No network calls without opt-in
- [ ] Section added to `copilot-instructions.md` (when/how to call)
- [ ] README.md describes the tool

---

## Example: Minimal Tool

A complete minimal tool in 3 files:

**`tools/hello-check/pyproject.toml`**
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hello-check"
version = "0.1.0"
description = "Checks if a hello.py file exists and is valid"
requires-python = ">=3.10"

[project.scripts]
hello-check = "hello_check.cli:main"
```

**`tools/hello-check/hello_check/cli.py`**
```python
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def main():
    parser = argparse.ArgumentParser(prog="hello-check")
    parser.add_argument("file", help="Python file to check")
    parser.add_argument("--cwd", default=".")
    args = parser.parse_args()

    target = Path(args.cwd) / args.file
    if not target.exists():
        print(f"❌ {args.file} not found")
        sys.exit(1)
    
    content = target.read_text()
    if "def " not in content:
        print(f"❌ {args.file} has no functions")
        sys.exit(1)
    
    print(f"✅ {args.file} exists and has functions")
    sys.exit(0)
```

**`tools/hello-check/tests/test_cli.py`**
```python
import subprocess, sys

def test_help():
    r = subprocess.run([sys.executable, "-m", "hello_check", "--help"], capture_output=True)
    assert r.returncode == 0
```
