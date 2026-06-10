"""YAML loader for pipeline definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from aipipeline.models import (
    Check,
    CommandCheck,
    ContainsTextCheck,
    DAG,
    DirExistsCheck,
    ExitCodeCheck,
    FailurePolicy,
    FileExistsCheck,
    RetryPolicy,
    Step,
)


def load_dag(source: Union[str, Path]) -> DAG:
    """Load a DAG from a YAML file.

    Supports a simplified YAML format for easy authoring:
    ```yaml
    name: My Pipeline
    steps:
      - id: build
        do: "Build the project"
        run: npm run build
        after: []
        check:
          - dist/ exists
          - exit code 0
    ```
    """
    path = Path(source)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    steps = []
    for raw_step in raw.get("steps", []):
        step = _parse_step(raw_step)
        steps.append(step)

    return DAG(
        name=raw.get("name", path.stem),
        description=raw.get("description", ""),
        steps=steps,
    )


def _parse_step(raw: dict) -> Step:
    """Parse a single step from simplified YAML."""
    step_id = raw.get("id", "")
    description = raw.get("do", raw.get("description", ""))
    action = raw.get("run", raw.get("action", ""))
    depends_on = raw.get("after", raw.get("depends_on", []))

    if isinstance(depends_on, str):
        depends_on = [depends_on]

    prechecks = [_parse_check(c) for c in raw.get("precheck", raw.get("prechecks", []))]
    postchecks = [_parse_check(c) for c in raw.get("check", raw.get("postchecks", []))]

    failure_policy = FailurePolicy()
    if raw.get("optional", False):
        failure_policy = FailurePolicy(
            on_precheck_failure="skip",
            on_execution_failure="continue",
            on_postcheck_failure="continue",
        )

    retry = RetryPolicy()
    if "retry" in raw:
        retry = RetryPolicy(**raw["retry"])

    return Step(
        id=step_id,
        description=description,
        action=action,
        depends_on=depends_on,
        prechecks=prechecks,
        postchecks=postchecks,
        failure_policy=failure_policy,
        retry=retry,
        timeout_seconds=raw.get("timeout", 300),
    )


def _parse_check(check_str: Union[str, dict]) -> Check:
    """Parse a check from a human-friendly string or dict.

    Supported string formats:
      - "path/to/file exists"         → FileExistsCheck
      - "path/to/dir/ exists"         → DirExistsCheck
      - "exit code 0"                 → ExitCodeCheck
      - "output contains 'text'"      → ContainsTextCheck
      - "run: command"                → CommandCheck
    """
    if isinstance(check_str, dict):
        return _parse_check_dict(check_str)

    s = check_str.strip()

    # "exit code N"
    if s.lower().startswith("exit code"):
        code = int(s.split()[-1])
        return ExitCodeCheck(expected=code, description=s)

    # "output contains 'text'"
    if "contains" in s.lower():
        parts = s.split("contains", 1)
        source = parts[0].strip().lower() if parts[0].strip() else "stdout"
        expected = parts[1].strip().strip("'\"")
        return ContainsTextCheck(source=source, expected=expected, description=s)

    # "run: command"
    if s.lower().startswith("run:"):
        cmd = s[4:].strip()
        return CommandCheck(command=cmd, description=s)

    # "path/ exists" (directory) or "path exists" (file)
    if s.endswith("exists"):
        path = s.replace("exists", "").strip()
        if path.endswith("/") or path.endswith("\\"):
            return DirExistsCheck(path=path.rstrip("/\\"), description=s)
        return FileExistsCheck(path=path, description=s)

    # Fallback: treat as a command check
    return CommandCheck(command=s, description=s)


def _parse_check_dict(d: dict) -> Check:
    """Parse a check from explicit dict format."""
    check_type = d.get("type", "command")
    if check_type == "file_exists":
        return FileExistsCheck(path=d["path"], description=d.get("description", ""))
    elif check_type == "dir_exists":
        return DirExistsCheck(path=d["path"], description=d.get("description", ""))
    elif check_type == "exit_code":
        return ExitCodeCheck(expected=d.get("expected", 0), description=d.get("description", ""))
    elif check_type == "contains_text":
        return ContainsTextCheck(
            source=d.get("source", "stdout"),
            expected=d.get("expected", ""),
            description=d.get("description", ""),
        )
    elif check_type == "command":
        return CommandCheck(command=d.get("command", ""), description=d.get("description", ""))
    else:
        return CommandCheck(command=str(d), description=f"Unknown: {d}")
