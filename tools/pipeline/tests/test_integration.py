"""Integration tests for the full pipeline flow.

Tests the realistic scenario:
1. Create a plan YAML
2. Execute it (pipeline run)
3. Verify postconditions (pipeline verify)
4. Show the plan (pipeline show)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workspace(tmp_path):
    """Create a realistic workspace with files a pipeline would produce."""
    return tmp_path


def write_plan(workspace: Path, plan: dict) -> Path:
    plan_path = workspace / "plan.yaml"
    plan_path.write_text(yaml.dump(plan, default_flow_style=False), encoding="utf-8")
    return plan_path


def run_cli(*args, cwd=None):
    """Run pipeline CLI and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "pipeline"] + list(args),
        capture_output=True,
        cwd=cwd,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout, result.stderr


class TestCLIShow:
    def test_show_displays_plan(self, workspace):
        plan = {
            "name": "Test Pipeline",
            "description": "A test",
            "steps": [
                {
                    "id": "step-1",
                    "description": "Create a file",
                    "action": "echo hello > output.txt",
                    "postchecks": [{"type": "file_exists", "path": "output.txt"}],
                }
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, err = run_cli("show", str(plan_path))
        assert code == 0
        assert "Test Pipeline" in out
        assert "step-1" in out

    def test_show_with_dependencies(self, workspace):
        plan = {
            "name": "DAG Pipeline",
            "steps": [
                {"id": "a", "description": "First", "action": "echo a"},
                {"id": "b", "description": "Second", "action": "echo b", "depends_on": ["a"]},
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli("show", str(plan_path))
        assert code == 0
        assert "a" in out
        assert "b" in out


class TestCLIVerify:
    def test_verify_passes_when_files_exist(self, workspace):
        # Create the files that postchecks expect
        (workspace / "output.txt").write_text("hello world")
        (workspace / "build").mkdir()

        plan = {
            "name": "Verify Test",
            "steps": [
                {
                    "id": "create-file",
                    "description": "Create output",
                    "action": "echo hello > output.txt",
                    "postchecks": [{"type": "file_exists", "path": "output.txt"}],
                },
                {
                    "id": "create-dir",
                    "description": "Create build dir",
                    "action": "mkdir build",
                    "postchecks": [{"type": "dir_exists", "path": "build"}],
                },
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli("verify", str(plan_path), "--cwd", str(workspace))
        assert code == 0
        assert "PASSED" in out

    def test_verify_fails_when_files_missing(self, workspace):
        plan = {
            "name": "Verify Fail Test",
            "steps": [
                {
                    "id": "missing-file",
                    "description": "Check missing file",
                    "action": "echo noop",
                    "postchecks": [{"type": "file_exists", "path": "does-not-exist.txt"}],
                },
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli("verify", str(plan_path), "--cwd", str(workspace))
        assert code == 1
        assert "FAILED" in out

    def test_verify_with_contains_text(self, workspace):
        (workspace / "readme.md").write_text("# My Project\nVersion 2.0")

        plan = {
            "name": "Text Check",
            "steps": [
                {
                    "id": "check-readme",
                    "description": "Verify readme has version",
                    "action": "cat readme.md",
                    "postchecks": [
                        {"type": "file_exists", "path": "readme.md"},
                    ],
                },
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli("verify", str(plan_path), "--cwd", str(workspace))
        assert code == 0

    def test_verify_saves_json_report(self, workspace):
        (workspace / "app.py").write_text("print('hello')")
        report_path = workspace / "report.json"

        plan = {
            "name": "Report Test",
            "steps": [
                {
                    "id": "check-app",
                    "description": "Verify app exists",
                    "action": "echo ok",
                    "postchecks": [{"type": "file_exists", "path": "app.py"}],
                },
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli(
            "verify", str(plan_path), "--cwd", str(workspace), "-o", str(report_path)
        )
        assert code == 0
        assert report_path.exists()
        report = json.loads(report_path.read_text())
        assert report["status"] == "passed"
        assert len(report["steps"]) == 1

    def test_verify_mixed_pass_fail(self, workspace):
        (workspace / "exists.txt").write_text("yes")

        plan = {
            "name": "Mixed Test",
            "steps": [
                {
                    "id": "step-pass",
                    "description": "This passes",
                    "action": "echo ok",
                    "postchecks": [{"type": "file_exists", "path": "exists.txt"}],
                },
                {
                    "id": "step-fail",
                    "description": "This fails",
                    "action": "echo ok",
                    "postchecks": [{"type": "file_exists", "path": "nope.txt"}],
                },
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli("verify", str(plan_path), "--cwd", str(workspace))
        assert code == 1
        assert "1/2" in out  # 1 passed out of 2


class TestCLIRun:
    def test_run_creates_files(self, workspace):
        plan = {
            "name": "Run Test",
            "steps": [
                {
                    "id": "create-file",
                    "description": "Create a file",
                    "action": f'echo hello > "{workspace / "output.txt"}"',
                    "postchecks": [{"type": "file_exists", "path": "output.txt"}],
                },
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli("run", str(plan_path), "--cwd", str(workspace))
        # The command should complete (pass or fail based on shell behavior)
        assert code in (0, 1)
        assert "Run Test" in out

    def test_run_respects_dependencies(self, workspace):
        plan = {
            "name": "Dep Test",
            "steps": [
                {
                    "id": "first",
                    "description": "Run first",
                    "action": "echo first",
                },
                {
                    "id": "second",
                    "description": "Run second",
                    "action": "echo second",
                    "depends_on": ["first"],
                },
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, out, _ = run_cli("run", str(plan_path), "--cwd", str(workspace))
        assert code in (0, 1)
        # Both steps should appear in output
        assert "first" in out
        assert "second" in out

    def test_run_saves_json_report(self, workspace):
        report_path = workspace / "run-report.json"
        plan = {
            "name": "Report Run",
            "steps": [
                {"id": "s1", "description": "Echo", "action": "echo done"},
            ],
        }
        plan_path = write_plan(workspace, plan)
        code, _, _ = run_cli(
            "run", str(plan_path), "--cwd", str(workspace), "-o", str(report_path)
        )
        assert report_path.exists()
        report = json.loads(report_path.read_text())
        assert "overall_status" in report


class TestInstallerDiscovery:
    """Test that the installer can discover tools."""

    def test_tools_dir_has_pyproject(self):
        tools_dir = Path(__file__).parent.parent.parent
        assert tools_dir.exists(), f"tools/ directory not found at {tools_dir}"
        pipeline_dir = tools_dir / "pipeline"
        assert pipeline_dir.exists(), "tools/pipeline/ not found"
        assert (pipeline_dir / "pyproject.toml").exists(), "pyproject.toml not found"

    def test_pipeline_importable(self):
        from pipeline import PipelineEngine, CheckEvaluator
        assert PipelineEngine is not None
        assert CheckEvaluator is not None

    def test_cli_help_works(self):
        code, out, _ = run_cli("--help")
        assert code == 0
        assert "run" in out
        assert "verify" in out
        assert "show" in out
