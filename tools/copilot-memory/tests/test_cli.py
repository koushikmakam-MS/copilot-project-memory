"""Integration tests for the copilot-memory CLI commands."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from copilot_memory.cli import cmd_status, cmd_verify, cmd_compact, cmd_init, cmd_schema_fix
from copilot_memory.store import _write_yaml, _write_json, MEMORY_ROOT


class FakeArgs:
    """Minimal args namespace for testing CLI commands."""
    def __init__(self, **kwargs):
        self.cwd = kwargs.get("cwd", None)
        self.fix = kwargs.get("fix", False)
        self.target = kwargs.get("target", "stdout")


@pytest.fixture
def mock_memory(tmp_path):
    """Create a complete mock project memory structure."""
    project_dir = tmp_path / "test-project-abc12345"
    project_dir.mkdir()

    # Core files
    _write_yaml(project_dir / "preferences.yml", {
        "schema_version": 1,
        "language": "python",
    })
    _write_yaml(project_dir / "rules.yml", {
        "schema_version": 1,
        "rules": [
            {
                "id": "use-python",
                "type": "do",
                "description": "Use Python",
                "learned_from": "explicit instruction",
                "created_at": "2026-06-11",
                "last_used": "2026-06-11",
                "use_count": 1,
                "share": False,
            },
        ],
    })
    _write_yaml(project_dir / "context.yml", {
        "schema_version": 1,
        "name": "TestProject",
        "description": "A test project",
        "stack": ["Python", "FastAPI"],
        "key_files": [],
        "notes": "",
    })
    _write_yaml(project_dir / "tracking.yml", {
        "schema_version": 1,
        "hotspots": [],
        "common_errors": [],
    })

    # Sessions
    sessions_dir = project_dir / "sessions" / "_default"
    sessions_dir.mkdir(parents=True)

    sid = "test-session-001"
    _write_json(sessions_dir / f"{sid}.json", {
        "sessionId": sid,
        "status": "active",
        "startedAt": "2026-06-11T10:00:00Z",
        "lastUpdatedAt": "2026-06-11T10:30:00Z",
        "summary": "Test session",
        "filesChanged": [],
        "decisions": [],
        "learnings": [],
    })
    _write_json(project_dir / "sessions" / "latest.json", {
        "lastSessionId": sid,
        "lastUpdatedAt": "2026-06-11T10:30:00Z",
        "activeSession": None,
    })

    # Global dir
    global_dir = tmp_path / "_global"
    global_dir.mkdir()
    _write_yaml(global_dir / "preferences.yml", {"schema_version": 1})
    _write_yaml(global_dir / "rules.yml", {"schema_version": 1, "rules": []})

    return tmp_path, project_dir


class TestCmdVerify:
    def test_verify_clean_project(self, mock_memory, capsys):
        tmp_path, project_dir = mock_memory

        with patch("copilot_memory.cli.find_project_dir", return_value=project_dir), \
             patch("copilot_memory.cli.GLOBAL_DIR", tmp_path / "_global"):
            code = cmd_verify(FakeArgs())

        assert code == 0
        output = capsys.readouterr().out
        assert "All checks passed" in output

    def test_verify_detects_missing_schema(self, mock_memory, capsys):
        tmp_path, project_dir = mock_memory

        # Remove schema_version from a file
        data = yaml.safe_load((project_dir / "rules.yml").read_text(encoding="utf-8"))
        del data["schema_version"]
        (project_dir / "rules.yml").write_text(
            yaml.dump(data), encoding="utf-8"
        )

        with patch("copilot_memory.cli.find_project_dir", return_value=project_dir):
            code = cmd_verify(FakeArgs())

        # Missing schema_version is a warning, not a hard error
        output = capsys.readouterr().out
        assert "schema_version" in output

    def test_verify_fix_adds_schema(self, mock_memory, capsys):
        tmp_path, project_dir = mock_memory

        # Remove schema_version
        data = yaml.safe_load((project_dir / "rules.yml").read_text(encoding="utf-8"))
        del data["schema_version"]
        (project_dir / "rules.yml").write_text(
            yaml.dump(data), encoding="utf-8"
        )

        with patch("copilot_memory.cli.find_project_dir", return_value=project_dir):
            code = cmd_verify(FakeArgs(fix=True))

        assert code == 0
        # Verify it was actually fixed
        fixed = yaml.safe_load((project_dir / "rules.yml").read_text(encoding="utf-8"))
        assert fixed["schema_version"] == 1

    def test_verify_detects_dangling_session(self, mock_memory, capsys):
        tmp_path, project_dir = mock_memory

        # Point latest to nonexistent session
        _write_json(project_dir / "sessions" / "latest.json", {
            "lastSessionId": "nonexistent-id",
            "lastUpdatedAt": "2026-06-11",
        })

        with patch("copilot_memory.cli.find_project_dir", return_value=project_dir):
            code = cmd_verify(FakeArgs())

        assert code == 1
        output = capsys.readouterr().out
        assert "Dangling" in output


class TestCmdCompact:
    def test_compact_prunes_excess_sessions(self, mock_memory, capsys):
        tmp_path, project_dir = mock_memory
        default_dir = project_dir / "sessions" / "_default"

        # Create 15 sessions (cap is 10)
        for i in range(15):
            _write_json(default_dir / f"session-{i:03d}.json", {
                "sessionId": f"session-{i:03d}",
                "status": "closed",
            })

        with patch("copilot_memory.cli.find_project_dir", return_value=project_dir):
            code = cmd_compact(FakeArgs())

        assert code == 0
        remaining = list(default_dir.glob("*.json"))
        assert len(remaining) <= 11  # 10 cap + the original test-session-001

    def test_compact_nothing_to_do(self, mock_memory, capsys):
        tmp_path, project_dir = mock_memory

        with patch("copilot_memory.cli.find_project_dir", return_value=project_dir):
            code = cmd_compact(FakeArgs())

        assert code == 0
        output = capsys.readouterr().out
        assert "Nothing to compact" in output


class TestCmdInit:
    def test_init_creates_project(self, tmp_path, capsys):
        work_dir = tmp_path / "new-project"
        work_dir.mkdir()

        with patch("copilot_memory.cli.find_project_dir", return_value=None), \
             patch("copilot_memory.cli.ensure_project_dir") as mock_ensure:
            project_dir = tmp_path / "new-project-12345678"
            project_dir.mkdir()
            mock_ensure.return_value = project_dir

            with patch("copilot_memory.store.TEMPLATE_DIR", tmp_path / "_no_template"):
                code = cmd_init(FakeArgs(cwd=str(work_dir)))

        assert code == 0
        output = capsys.readouterr().out
        assert "Project memory created" in output

    def test_init_skips_if_exists(self, mock_memory, capsys):
        tmp_path, project_dir = mock_memory

        with patch("copilot_memory.cli.find_project_dir", return_value=project_dir):
            code = cmd_init(FakeArgs())

        assert code == 0
        output = capsys.readouterr().out
        assert "already exists" in output


class TestCmdSchemaFix:
    def test_fixes_missing_schema_versions(self, tmp_path, capsys):
        # Create files without schema_version
        (tmp_path / "prefs.yml").write_text("language: python\n", encoding="utf-8")
        (tmp_path / "rules.yml").write_text("rules: []\n", encoding="utf-8")

        code = cmd_schema_fix(FakeArgs(cwd=str(tmp_path)))

        assert code == 0
        output = capsys.readouterr().out
        assert "Fixed 2 file(s)" in output

        # Verify fix
        for fname in ["prefs.yml", "rules.yml"]:
            data = yaml.safe_load((tmp_path / fname).read_text(encoding="utf-8"))
            assert data["schema_version"] == 1

    def test_skips_already_valid(self, tmp_path, capsys):
        _write_yaml(tmp_path / "test.yml", {"schema_version": 1, "key": "val"})

        code = cmd_schema_fix(FakeArgs(cwd=str(tmp_path)))

        assert code == 0
        output = capsys.readouterr().out
        assert "already have schema_version" in output
