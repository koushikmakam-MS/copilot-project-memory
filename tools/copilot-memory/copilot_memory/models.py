"""Pydantic models for all project memory YAML/JSON files.

These models are the single source of truth for file schemas.
Every read/write goes through validation — no more silent corruption.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class Rule(BaseModel):
    """A single do/don't rule."""
    id: str
    type: str  # "do" or "dont"
    description: str
    learned_from: str = "explicit instruction"
    created_at: str = ""
    last_used: str = ""
    use_count: int = 0
    share: bool = False

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("do", "dont"):
            raise ValueError(f"Rule type must be 'do' or 'dont', got '{v}'")
        return v

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not re.match(r"^[a-z0-9][a-z0-9\-_]*$", v):
            raise ValueError(
                f"Rule id must be lowercase alphanumeric with hyphens/underscores: '{v}'"
            )
        return v


class RulesFile(BaseModel):
    """Schema for rules.yml files."""
    schema_version: int = 1
    rules: list[Rule] = []


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class ContextFile(BaseModel):
    """Schema for context.yml files."""
    schema_version: int = 1
    name: str = ""
    description: str = ""
    stack: list[str] = []
    key_files: list[str] = []
    notes: str = ""


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class SessionEntry(BaseModel):
    """A single session record."""
    sessionId: str
    status: str = "active"  # active | closed | abandoned
    startedAt: str = ""
    lastUpdatedAt: str = ""
    endedAt: Optional[str] = None
    summary: str = ""
    filesChanged: list[str] = []
    decisions: list[str] = []
    learnings: list[str] = []
    compactedSummary: str = ""
    compactionCount: int = 0
    parents: list[str] = []

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("active", "closed", "abandoned"):
            raise ValueError(f"Session status must be active/closed/abandoned, got '{v}'")
        return v


class LatestSession(BaseModel):
    """Schema for sessions/latest.json."""
    lastSessionId: str
    lastUpdatedAt: str = ""
    activeSession: Optional[str] = None


# ---------------------------------------------------------------------------
# Verification results
# ---------------------------------------------------------------------------

class FileCheck(BaseModel):
    """Result of checking a single memory file."""
    path: str
    status: str  # ok | missing | malformed | recreated
    detail: str = ""


class VerifyReport(BaseModel):
    """Full verification report."""
    project: str
    checks: list[FileCheck] = []
    total_size_bytes: int = 0
    dangling_sessions: list[str] = []
    mismatched_ids: list[str] = []

    @property
    def has_errors(self) -> bool:
        return any(
            c.status in ("malformed", "missing")
            for c in self.checks
        ) or bool(self.dangling_sessions) or bool(self.mismatched_ids)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """Current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def generate_rule_id(description: str) -> str:
    """Generate a kebab-case rule ID from a description."""
    slug = re.sub(r"[^a-z0-9]+", "-", description.lower()).strip("-")
    return slug[:50]


def detect_rule_type(description: str) -> str:
    """Auto-detect do/dont from description text."""
    lower = description.lower().strip()
    dont_prefixes = ("never", "don't", "dont", "avoid", "no ", "stop")
    for prefix in dont_prefixes:
        if lower.startswith(prefix):
            return "dont"
    return "do"
