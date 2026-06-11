"""Tests for Pydantic models — schema validation is the first line of defense."""

import pytest
from copilot_memory.models import (
    Rule,
    RulesFile,
    ContextFile,
    SessionEntry,
    LatestSession,
    VerifyReport,
    FileCheck,
    generate_rule_id,
    detect_rule_type,
)


class TestRule:
    def test_valid_rule(self):
        r = Rule(id="use-typescript", type="do", description="Always use TypeScript")
        assert r.id == "use-typescript"
        assert r.type == "do"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValueError, match="do.*dont"):
            Rule(id="test", type="maybe", description="test")

    def test_invalid_id_rejected(self):
        with pytest.raises(ValueError, match="lowercase"):
            Rule(id="Use TypeScript!", type="do", description="test")

    def test_uppercase_id_rejected(self):
        with pytest.raises(ValueError, match="lowercase"):
            Rule(id="UseTypeScript", type="do", description="test")

    def test_hyphen_underscore_allowed(self):
        r = Rule(id="use-type_script", type="do", description="test")
        assert r.id == "use-type_script"

    def test_defaults(self):
        r = Rule(id="test-rule", type="do", description="test")
        assert r.use_count == 0
        assert r.share is False
        assert r.learned_from == "explicit instruction"


class TestRulesFile:
    def test_empty_rules(self):
        rf = RulesFile()
        assert rf.schema_version == 1
        assert rf.rules == []

    def test_with_rules(self):
        rf = RulesFile(rules=[
            Rule(id="r1", type="do", description="Do thing"),
            Rule(id="r2", type="dont", description="Don't do thing"),
        ])
        assert len(rf.rules) == 2


class TestContextFile:
    def test_defaults(self):
        ctx = ContextFile()
        assert ctx.schema_version == 1
        assert ctx.name == ""
        assert ctx.stack == []

    def test_with_data(self):
        ctx = ContextFile(name="MyProject", stack=["Python", "FastAPI"])
        assert ctx.name == "MyProject"
        assert len(ctx.stack) == 2


class TestSessionEntry:
    def test_valid_session(self):
        s = SessionEntry(sessionId="abc-123", status="active")
        assert s.status == "active"

    def test_invalid_status(self):
        with pytest.raises(ValueError, match="active.*closed.*abandoned"):
            SessionEntry(sessionId="abc", status="running")

    def test_defaults(self):
        s = SessionEntry(sessionId="abc")
        assert s.filesChanged == []
        assert s.decisions == []
        assert s.summary == ""


class TestLatestSession:
    def test_valid(self):
        ls = LatestSession(lastSessionId="abc-123")
        assert ls.activeSession is None


class TestVerifyReport:
    def test_no_errors(self):
        r = VerifyReport(
            project="test",
            checks=[FileCheck(path="rules.yml", status="ok")],
        )
        assert not r.has_errors

    def test_has_errors_on_missing(self):
        r = VerifyReport(
            project="test",
            checks=[FileCheck(path="rules.yml", status="missing")],
        )
        assert r.has_errors

    def test_has_errors_on_dangling(self):
        r = VerifyReport(
            project="test",
            dangling_sessions=["abc -> missing"],
        )
        assert r.has_errors


class TestHelpers:
    def test_generate_rule_id(self):
        assert generate_rule_id("Always use TypeScript") == "always-use-typescript"
        assert generate_rule_id("Don't use ANY type!!!") == "don-t-use-any-type"
        assert len(generate_rule_id("x" * 100)) <= 50

    def test_detect_rule_type_do(self):
        assert detect_rule_type("Always use TypeScript") == "do"
        assert detect_rule_type("Use pnpm") == "do"
        assert detect_rule_type("Prefer concise answers") == "do"

    def test_detect_rule_type_dont(self):
        assert detect_rule_type("Never use any type") == "dont"
        assert detect_rule_type("Don't use console.log") == "dont"
        assert detect_rule_type("Avoid global variables") == "dont"
        assert detect_rule_type("stop using var") == "dont"
        assert detect_rule_type("No default exports") == "dont"
