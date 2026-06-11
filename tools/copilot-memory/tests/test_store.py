"""Tests for the store module — file I/O with validation."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from copilot_memory.models import Rule, RulesFile, ContextFile, SessionEntry, LatestSession
from copilot_memory.store import (
    _read_yaml,
    _write_yaml,
    _read_json,
    _write_json,
    load_rules,
    save_rules,
    load_context,
    save_context,
    load_prefs,
    save_prefs,
    load_latest_session,
    save_latest_session,
    load_session,
    check_session_integrity,
    make_project_slug,
)


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal project memory structure."""
    (tmp_path / "sessions" / "_default").mkdir(parents=True)
    return tmp_path


class TestYamlIO:
    def test_read_missing_file(self, tmp_path):
        assert _read_yaml(tmp_path / "nope.yml") == {}

    def test_read_empty_file(self, tmp_path):
        (tmp_path / "empty.yml").write_text("", encoding="utf-8")
        assert _read_yaml(tmp_path / "empty.yml") == {}

    def test_write_adds_schema_version(self, tmp_path):
        fpath = tmp_path / "test.yml"
        _write_yaml(fpath, {"key": "value"})
        data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1
        assert data["key"] == "value"

    def test_write_preserves_existing_schema_version(self, tmp_path):
        fpath = tmp_path / "test.yml"
        _write_yaml(fpath, {"schema_version": 2, "key": "value"})
        data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        assert data["schema_version"] == 2

    def test_write_creates_parent_dirs(self, tmp_path):
        fpath = tmp_path / "deep" / "nested" / "test.yml"
        _write_yaml(fpath, {"x": 1})
        assert fpath.exists()

    def test_atomic_write_no_partial(self, tmp_path):
        """Temp file should not persist after successful write."""
        fpath = tmp_path / "test.yml"
        _write_yaml(fpath, {"x": 1})
        assert not (tmp_path / "test.tmp").exists()


class TestJsonIO:
    def test_read_missing(self, tmp_path):
        assert _read_json(tmp_path / "nope.json") == {}

    def test_roundtrip(self, tmp_path):
        fpath = tmp_path / "test.json"
        _write_json(fpath, {"key": "value", "num": 42})
        data = _read_json(fpath)
        assert data["key"] == "value"
        assert data["num"] == 42


class TestRulesOperations:
    def test_load_empty(self, tmp_project):
        rules = load_rules(tmp_project)
        assert rules.rules == []
        assert rules.schema_version == 1

    def test_save_and_load(self, tmp_project):
        rf = RulesFile(rules=[
            Rule(id="use-ts", type="do", description="Use TypeScript"),
            Rule(id="no-any", type="dont", description="Never use any"),
        ])
        save_rules(tmp_project, rf)
        loaded = load_rules(tmp_project)
        assert len(loaded.rules) == 2
        assert loaded.rules[0].id == "use-ts"
        assert loaded.rules[1].type == "dont"

    def test_load_skips_malformed_rules(self, tmp_project):
        """Rules with missing/invalid fields should be skipped, not crash."""
        _write_yaml(tmp_project / "rules.yml", {
            "schema_version": 1,
            "rules": [
                {"id": "good-rule", "type": "do", "description": "Valid"},
                {"type": "do", "description": "Missing ID"},  # no id
                {"id": "Bad ID!", "type": "do", "description": "Invalid ID"},
                {"id": "good-two", "type": "do", "description": "Also valid"},
            ],
        })
        rules = load_rules(tmp_project)
        assert len(rules.rules) == 2
        assert rules.rules[0].id == "good-rule"
        assert rules.rules[1].id == "good-two"

    def test_saved_file_has_schema_version(self, tmp_project):
        save_rules(tmp_project, RulesFile())
        data = yaml.safe_load(
            (tmp_project / "rules.yml").read_text(encoding="utf-8")
        )
        assert data["schema_version"] == 1


class TestContextOperations:
    def test_load_empty(self, tmp_project):
        ctx = load_context(tmp_project)
        assert ctx.name == ""
        assert ctx.stack == []

    def test_save_and_load(self, tmp_project):
        ctx = ContextFile(name="TestProject", stack=["Python", "FastAPI"])
        save_context(tmp_project, ctx)
        loaded = load_context(tmp_project)
        assert loaded.name == "TestProject"
        assert loaded.stack == ["Python", "FastAPI"]


class TestPrefsOperations:
    def test_load_empty(self, tmp_project):
        prefs = load_prefs(tmp_project)
        assert prefs["schema_version"] == 1

    def test_save_and_load(self, tmp_project):
        save_prefs(tmp_project, {
            "language": "typescript",
            "indent": 2,
        })
        loaded = load_prefs(tmp_project)
        assert loaded["language"] == "typescript"
        assert loaded["indent"] == 2
        assert loaded["schema_version"] == 1  # auto-added


class TestSessionOperations:
    def test_load_latest_empty(self, tmp_project):
        assert load_latest_session(tmp_project) is None

    def test_save_and_load_latest(self, tmp_project):
        latest = LatestSession(lastSessionId="abc-123", lastUpdatedAt="2026-06-11")
        save_latest_session(tmp_project, latest)
        loaded = load_latest_session(tmp_project)
        assert loaded is not None
        assert loaded.lastSessionId == "abc-123"

    def test_load_session_file(self, tmp_project):
        session_data = {
            "sessionId": "test-session-1",
            "status": "active",
            "startedAt": "2026-06-11T10:00:00Z",
            "lastUpdatedAt": "2026-06-11T10:30:00Z",
            "summary": "Test session",
        }
        fpath = tmp_project / "sessions" / "_default" / "test-session-1.json"
        fpath.write_text(json.dumps(session_data), encoding="utf-8")

        entry = load_session(fpath)
        assert entry is not None
        assert entry.sessionId == "test-session-1"
        assert entry.status == "active"


class TestSessionIntegrity:
    def test_detects_dangling_pointer(self, tmp_project):
        _write_json(tmp_project / "sessions" / "latest.json", {
            "lastSessionId": "nonexistent-id",
            "lastUpdatedAt": "2026-06-11",
        })
        dangling, mismatched = check_session_integrity(tmp_project)
        assert len(dangling) == 1
        assert "nonexistent-id" in dangling[0]

    def test_detects_id_mismatch(self, tmp_project):
        fpath = tmp_project / "sessions" / "_default" / "file-name-id.json"
        fpath.write_text(json.dumps({
            "sessionId": "different-id",
            "status": "active",
        }), encoding="utf-8")

        dangling, mismatched = check_session_integrity(tmp_project)
        assert len(mismatched) == 1
        assert "file-name-id" in mismatched[0]
        assert "different-id" in mismatched[0]

    def test_clean_state_no_issues(self, tmp_project):
        # Create a valid session
        sid = "valid-session-1"
        fpath = tmp_project / "sessions" / "_default" / f"{sid}.json"
        fpath.write_text(json.dumps({
            "sessionId": sid,
            "status": "active",
        }), encoding="utf-8")
        _write_json(tmp_project / "sessions" / "latest.json", {
            "lastSessionId": sid,
            "lastUpdatedAt": "2026-06-11",
        })

        dangling, mismatched = check_session_integrity(tmp_project)
        assert len(dangling) == 0
        assert len(mismatched) == 0


class TestProjectSlug:
    def test_basic_slug(self):
        slug = make_project_slug("/home/user/my-project")
        assert slug.startswith("my-project-")
        assert len(slug.split("-")[-1]) == 8  # hash suffix

    def test_underscores_converted(self):
        slug = make_project_slug("/repo/AI_BlackBox")
        assert slug.startswith("ai-blackbox-")

    def test_deterministic(self):
        slug1 = make_project_slug("/repo/test")
        slug2 = make_project_slug("/repo/test")
        assert slug1 == slug2

    def test_different_paths_different_hashes(self):
        slug1 = make_project_slug("/repo/project-a")
        slug2 = make_project_slug("/repo/project-b")
        assert slug1 != slug2
