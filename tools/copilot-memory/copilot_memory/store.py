"""File I/O and path resolution for project memory.

Handles all reads/writes with Pydantic validation.
Ensures schema_version, atomic writes, and structural integrity.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import yaml

from copilot_memory.models import (
    ContextFile,
    LatestSession,
    Rule,
    RulesFile,
    SessionEntry,
)


MEMORY_ROOT = Path.home() / ".copilot" / "project-memory"
GLOBAL_DIR = MEMORY_ROOT / "_global"
TEMPLATE_DIR = MEMORY_ROOT / "_template"

# Expected files in every project folder
EXPECTED_FILES = [
    "preferences.yml",
    "rules.yml",
    "context.yml",
    "tracking.yml",
]


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def get_git_root(cwd: Optional[str] = None) -> Optional[str]:
    """Get the git repository root, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=cwd or os.getcwd(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def make_project_slug(path: str) -> str:
    """Create a project slug from a path: leaf-name + short hash."""
    normalized = os.path.normpath(path)
    leaf = os.path.basename(normalized)
    slug = leaf.lower().replace("_", "-").replace(" ", "-")
    path_hash = hashlib.sha256(normalized.encode()).hexdigest()[:8]
    return f"{slug}-{path_hash}"


def find_project_dir(cwd: Optional[str] = None) -> Optional[Path]:
    """Find the project memory folder for the current working directory.

    Strategy:
    1. Get git root (or use cwd)
    2. Compute expected slug prefix (leaf name)
    3. Scan MEMORY_ROOT for matching folder
    """
    work_dir = cwd or os.getcwd()
    root = get_git_root(work_dir) or work_dir
    leaf = os.path.basename(os.path.normpath(root)).lower().replace("_", "-").replace(" ", "-")

    if not MEMORY_ROOT.exists():
        return None

    # Normalize the leaf for comparison (hyphens and underscores are equivalent)
    leaf_normalized = leaf.replace("_", "-")

    for d in MEMORY_ROOT.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        # Normalize folder name the same way
        folder_normalized = d.name.replace("_", "-")
        # Match by prefix (e.g., "ai-blackbox" matches "ai-blackbox-ae8e6c7c"
        # and also "ai_blackbox-ae8e6c7c")
        if folder_normalized.startswith(leaf_normalized):
            return d

    return None


def ensure_project_dir(cwd: Optional[str] = None) -> Path:
    """Find or create the project memory folder."""
    existing = find_project_dir(cwd)
    if existing:
        return existing

    work_dir = cwd or os.getcwd()
    root = get_git_root(work_dir) or work_dir
    slug = make_project_slug(root)
    project_dir = MEMORY_ROOT / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


# ---------------------------------------------------------------------------
# YAML I/O with schema enforcement
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict:
    """Read a YAML file, returning empty dict if missing/empty.
    
    Warns if the file contains content that doesn't parse to a dict.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig").strip()  # utf-8-sig handles BOM
    if not text:
        return {}
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        import sys
        print(f"Warning: {path} contains non-dict YAML ({type(data).__name__}), treating as empty", file=sys.stderr)
        return {}
    return data


def _write_yaml(path: Path, data: dict) -> None:
    """Write YAML atomically with schema_version enforcement."""
    if "schema_version" not in data:
        data["schema_version"] = 1
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to temp file first, then rename (atomic on same filesystem)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def _read_json(path: Path) -> dict:
    """Read a JSON file, returning empty dict if missing."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig").strip()  # utf-8-sig handles BOM
    if not text:
        return {}
    return json.loads(text)


def _write_json(path: Path, data: dict) -> None:
    """Write JSON atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Rules operations
# ---------------------------------------------------------------------------

def load_rules(project_dir: Path) -> RulesFile:
    """Load and validate rules.yml."""
    raw = _read_yaml(project_dir / "rules.yml")
    rules_list = raw.get("rules", [])
    validated = []
    for r in rules_list:
        if isinstance(r, dict) and r.get("id"):
            try:
                validated.append(Rule(**r))
            except Exception:
                pass  # skip malformed rules
    return RulesFile(
        schema_version=raw.get("schema_version", 1),
        rules=validated,
    )


def save_rules(project_dir: Path, rules_file: RulesFile) -> None:
    """Save rules.yml with validation."""
    data = {
        "schema_version": rules_file.schema_version,
        "rules": [r.model_dump() for r in rules_file.rules],
    }
    _write_yaml(project_dir / "rules.yml", data)


# ---------------------------------------------------------------------------
# Context operations
# ---------------------------------------------------------------------------

def load_context(project_dir: Path) -> ContextFile:
    """Load and validate context.yml."""
    raw = _read_yaml(project_dir / "context.yml")
    return ContextFile(**{k: v for k, v in raw.items() if k != "schema_version"},
                       schema_version=raw.get("schema_version", 1))


def save_context(project_dir: Path, context: ContextFile) -> None:
    """Save context.yml with validation."""
    _write_yaml(project_dir / "context.yml", context.model_dump())


# ---------------------------------------------------------------------------
# Preferences operations (dynamic key-value, less strict)
# ---------------------------------------------------------------------------

def load_prefs(project_dir: Path) -> dict:
    """Load preferences.yml as a dict."""
    data = _read_yaml(project_dir / "preferences.yml")
    if "schema_version" not in data:
        data["schema_version"] = 1
    return data


def save_prefs(project_dir: Path, prefs: dict) -> None:
    """Save preferences.yml."""
    _write_yaml(project_dir / "preferences.yml", prefs)


# ---------------------------------------------------------------------------
# Session operations
# ---------------------------------------------------------------------------

def load_latest_session(project_dir: Path) -> Optional[LatestSession]:
    """Load sessions/latest.json."""
    path = project_dir / "sessions" / "latest.json"
    raw = _read_json(path)
    if not raw or "lastSessionId" not in raw:
        return None
    try:
        return LatestSession(**raw)
    except Exception:
        return None


def save_latest_session(project_dir: Path, latest: LatestSession) -> None:
    """Save sessions/latest.json."""
    _write_json(project_dir / "sessions" / "latest.json", latest.model_dump())


def find_session_file(project_dir: Path, session_id: str) -> Optional[Path]:
    """Find a session JSON file by ID, searching all session subdirs."""
    sessions_dir = project_dir / "sessions"
    if not sessions_dir.exists():
        return None

    for path in sessions_dir.rglob("*.json"):
        if path.name == "latest.json":
            continue
        if session_id in path.stem:
            return path
        # Also check inside the file
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("sessionId") == session_id:
                return path
        except Exception:
            continue
    return None


def load_session(path: Path) -> Optional[SessionEntry]:
    """Load and validate a session JSON file."""
    raw = _read_json(path)
    if not raw or "sessionId" not in raw:
        return None
    try:
        return SessionEntry(**raw)
    except Exception:
        return None


def list_sessions(project_dir: Path) -> list[tuple[Path, SessionEntry]]:
    """List all valid session files with their parsed data."""
    sessions_dir = project_dir / "sessions"
    if not sessions_dir.exists():
        return []

    results = []
    for path in sessions_dir.rglob("*.json"):
        if path.name == "latest.json":
            continue
        entry = load_session(path)
        if entry:
            results.append((path, entry))

    results.sort(key=lambda x: x[1].lastUpdatedAt or x[1].startedAt, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Integrity checks
# ---------------------------------------------------------------------------

def check_session_integrity(project_dir: Path) -> tuple[list[str], list[str]]:
    """Check for dangling pointers and filename/ID mismatches.

    Returns (dangling_sessions, mismatched_ids).
    """
    dangling = []
    mismatched = []

    # Check latest.json points to a real session
    latest = load_latest_session(project_dir)
    if latest and latest.lastSessionId:  # skip empty/blank IDs (fresh init)
        found = find_session_file(project_dir, latest.lastSessionId)
        if not found:
            dangling.append(
                f"latest.json -> {latest.lastSessionId} (file not found)"
            )

    # Check filename matches sessionId
    sessions_dir = project_dir / "sessions"
    if sessions_dir.exists():
        for path in sessions_dir.rglob("*.json"):
            if path.name == "latest.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                file_id = path.stem
                session_id = data.get("sessionId", "")
                if session_id and session_id != file_id:
                    mismatched.append(
                        f"file={file_id} != sessionId={session_id} in {path}"
                    )
            except Exception:
                continue

    return dangling, mismatched


def get_dir_size(path: Path) -> int:
    """Get total size of all files in a directory tree."""
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total
