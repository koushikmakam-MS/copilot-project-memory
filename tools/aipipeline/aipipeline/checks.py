"""Check evaluators — deterministic verification of pre/post conditions."""

from __future__ import annotations

import os
import subprocess
from typing import Optional

from aipipeline.models import (
    BaseCheck,
    Check,
    CheckResult,
    CommandCheck,
    ContainsTextCheck,
    CustomCheck,
    DirExistsCheck,
    ExecutionResult,
    ExitCodeCheck,
    FileExistsCheck,
)


class CheckEvaluator:
    """Evaluates typed checks against the environment or execution results."""

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd or os.getcwd()

    def evaluate(
        self,
        checks: list[Check],
        exec_result: Optional[ExecutionResult] = None,
    ) -> list[CheckResult]:
        results = []
        for check in checks:
            result = self._evaluate_one(check, exec_result)
            results.append(result)
        return results

    def _evaluate_one(
        self,
        check: Check,
        exec_result: Optional[ExecutionResult],
    ) -> CheckResult:
        if isinstance(check, FileExistsCheck):
            return self._check_file_exists(check)
        elif isinstance(check, DirExistsCheck):
            return self._check_dir_exists(check)
        elif isinstance(check, ExitCodeCheck):
            return self._check_exit_code(check, exec_result)
        elif isinstance(check, ContainsTextCheck):
            return self._check_contains_text(check, exec_result)
        elif isinstance(check, CommandCheck):
            return self._check_command(check)
        elif isinstance(check, CustomCheck):
            return self._check_custom(check)
        else:
            return CheckResult(
                check_type="unknown",
                description=getattr(check, "description", "Unknown check"),
                passed=False,
                evidence=f"Unknown check type: {type(check).__name__}",
            )

    def _check_file_exists(self, check: FileExistsCheck) -> CheckResult:
        path = os.path.join(self.cwd, check.path) if not os.path.isabs(check.path) else check.path
        exists = os.path.isfile(path)
        return CheckResult(
            check_type="file_exists",
            description=check.description or f"File exists: {check.path}",
            passed=exists,
            evidence=f"{'Found' if exists else 'Not found'}: {path}",
            verification_strength="deterministic",
        )

    def _check_dir_exists(self, check: DirExistsCheck) -> CheckResult:
        path = os.path.join(self.cwd, check.path) if not os.path.isabs(check.path) else check.path
        exists = os.path.isdir(path)
        return CheckResult(
            check_type="dir_exists",
            description=check.description or f"Directory exists: {check.path}",
            passed=exists,
            evidence=f"{'Found' if exists else 'Not found'}: {path}",
            verification_strength="deterministic",
        )

    def _check_exit_code(
        self, check: ExitCodeCheck, exec_result: Optional[ExecutionResult]
    ) -> CheckResult:
        if exec_result is None or exec_result.exit_code is None:
            return CheckResult(
                check_type="exit_code",
                description=check.description or f"Exit code == {check.expected}",
                passed=False,
                evidence="No execution result available",
            )
        passed = exec_result.exit_code == check.expected
        return CheckResult(
            check_type="exit_code",
            description=check.description or f"Exit code == {check.expected}",
            passed=passed,
            evidence=f"Got exit code {exec_result.exit_code}, expected {check.expected}",
            verification_strength="deterministic",
        )

    def _check_contains_text(
        self, check: ContainsTextCheck, exec_result: Optional[ExecutionResult]
    ) -> CheckResult:
        text = ""
        source_label = check.source

        if check.source == "stdout" and exec_result:
            text = exec_result.output
        elif check.source == "stderr" and exec_result:
            text = exec_result.error or ""
        elif check.source.startswith("file:"):
            fpath = check.source[5:]
            fpath = os.path.join(self.cwd, fpath) if not os.path.isabs(fpath) else fpath
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()
                source_label = f"file:{fpath}"
            except FileNotFoundError:
                return CheckResult(
                    check_type="contains_text",
                    description=check.description,
                    passed=False,
                    evidence=f"File not found: {fpath}",
                )

        found = check.expected in text
        return CheckResult(
            check_type="contains_text",
            description=check.description or f"'{check.expected}' in {source_label}",
            passed=found,
            evidence=f"{'Found' if found else 'Not found'} '{check.expected}' in {source_label}",
            verification_strength="deterministic",
        )

    def _check_command(self, check: CommandCheck) -> CheckResult:
        try:
            result = subprocess.run(
                check.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.cwd,
            )
            passed = result.returncode == 0
            return CheckResult(
                check_type="command",
                description=check.description or f"Command: {check.command}",
                passed=passed,
                evidence=f"exit={result.returncode} stdout={result.stdout[:200]}",
                verification_strength="deterministic",
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                check_type="command",
                description=check.description or f"Command: {check.command}",
                passed=False,
                evidence="Command timed out (30s)",
            )
        except Exception as e:
            return CheckResult(
                check_type="command",
                description=check.description or f"Command: {check.command}",
                passed=False,
                evidence=f"Error: {e}",
            )

    def _check_custom(self, check: CustomCheck) -> CheckResult:
        if check.check_fn is None:
            return CheckResult(
                check_type="custom",
                description=check.description,
                passed=False,
                evidence="No check function provided",
                verification_strength="custom",
            )
        try:
            result = check.check_fn()
            passed = bool(result)
            return CheckResult(
                check_type="custom",
                description=check.description,
                passed=passed,
                evidence=f"Custom check returned: {result}",
                verification_strength="custom",
            )
        except Exception as e:
            return CheckResult(
                check_type="custom",
                description=check.description,
                passed=False,
                evidence=f"Custom check raised: {e}",
                verification_strength="custom",
            )
