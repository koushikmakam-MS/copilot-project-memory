"""File I/O and path resolution for project memory.

Handles all reads/writes with Pydantic validation.
Ensures schema_version, atomic writes, and structural integrity.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

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
    """Read a JSON file, returning empty dict if missing.

    Transparently handles gzipped session files: if `path` has suffix `.gz`
    the bytes are gunzipped first. If a plain `.json` path is requested but
    only a `.json.gz` sibling exists, that sibling is read.
    """
    if path.suffix == ".gz":
        if not path.exists():
            return {}
        try:
            text = gzip.decompress(path.read_bytes()).decode("utf-8-sig").strip()
        except (OSError, UnicodeDecodeError):
            return {}
        return json.loads(text) if text else {}

    if not path.exists():
        # Fall back to the gzipped sibling if present
        gz = path.with_suffix(path.suffix + ".gz")
        if gz.exists():
            return _read_json(gz)
        return {}
    text = path.read_text(encoding="utf-8-sig").strip()  # utf-8-sig handles BOM
    if not text:
        return {}
    return json.loads(text)


def _iter_session_files(sessions_dir: Path) -> Iterable[Path]:
    """Yield every session file (both `.json` and `.json.gz`), excluding latest.json."""
    if not sessions_dir.exists():
        return
    for pattern in ("*.json", "*.json.gz"):
        for path in sessions_dir.rglob(pattern):
            if path.name == "latest.json":
                continue
            yield path


def _session_stem(path: Path) -> str:
    """Return the session ID stem for either `<id>.json` or `<id>.json.gz`."""
    name = path.name
    if name.endswith(".json.gz"):
        return name[:-len(".json.gz")]
    return path.stem


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
    """Find a session file by ID (searches `.json` and `.json.gz`)."""
    sessions_dir = project_dir / "sessions"
    for path in _iter_session_files(sessions_dir):
        if session_id in _session_stem(path):
            return path
        raw = _read_json(path)
        if raw.get("sessionId") == session_id:
            return path
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


# Compaction thresholds — crossing any of these means the session should be
# rewritten with older entries collapsed into `compactedSummary`.
COMPACT_ENTRIES_THRESHOLD = 20   # len(decisions) + len(learnings)
COMPACT_FILES_THRESHOLD = 30     # len(filesChanged)
COMPACT_SIZE_THRESHOLD = 8 * 1024  # serialized JSON bytes


def session_needs_compaction(entry: SessionEntry) -> tuple[bool, list[str]]:
    """Return (needs_compaction, reasons) for a session entry.

    Deterministic size gate — no LLM, no I/O. The AI-side auto-save uses this
    signal to decide whether to rewrite older decisions/learnings into a
    prose `compactedSummary` before persisting.
    """
    reasons: list[str] = []
    if len(entry.decisions) + len(entry.learnings) > COMPACT_ENTRIES_THRESHOLD:
        reasons.append(
            f"decisions+learnings={len(entry.decisions) + len(entry.learnings)} > {COMPACT_ENTRIES_THRESHOLD}"
        )
    if len(entry.filesChanged) > COMPACT_FILES_THRESHOLD:
        reasons.append(
            f"filesChanged={len(entry.filesChanged)} > {COMPACT_FILES_THRESHOLD}"
        )
    size = len(json.dumps(entry.model_dump()).encode("utf-8"))
    if size > COMPACT_SIZE_THRESHOLD:
        reasons.append(f"size={size}B > {COMPACT_SIZE_THRESHOLD}B")
    return (bool(reasons), reasons)


def list_sessions(project_dir: Path) -> list[tuple[Path, SessionEntry]]:
    """List all valid session files with their parsed data (incl. gzipped)."""
    results = []
    for path in _iter_session_files(project_dir / "sessions"):
        entry = load_session(path)
        if entry:
            results.append((path, entry))

    results.sort(key=lambda x: x[1].lastUpdatedAt or x[1].startedAt, reverse=True)
    return results


# Cap on decisions/learnings retained verbatim in a merged session before the
# rest are pushed into `compactedSummary`.
MERGE_VERBATIM_KEEP = 5


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _digest_parent(entry: SessionEntry) -> str:
    """Build a compact prose digest of a parent session for merging."""
    lines = [f"**From `{entry.sessionId}`** ({entry.status}):"]
    if entry.summary:
        lines.append(f"  summary: {entry.summary}")
    if entry.decisions:
        lines.append(f"  decisions ({len(entry.decisions)}): " +
                     "; ".join(entry.decisions[:10]) +
                     ("…" if len(entry.decisions) > 10 else ""))
    if entry.learnings:
        lines.append(f"  learnings ({len(entry.learnings)}): " +
                     "; ".join(entry.learnings[:10]) +
                     ("…" if len(entry.learnings) > 10 else ""))
    if entry.filesChanged:
        lines.append(f"  files ({len(entry.filesChanged)}): " +
                     ", ".join(entry.filesChanged[:10]) +
                     ("…" if len(entry.filesChanged) > 10 else ""))
    if entry.compactedSummary:
        lines.append(f"  prior compaction: {entry.compactedSummary[:400]}" +
                     ("…" if len(entry.compactedSummary) > 400 else ""))
    return "\n".join(lines)


def build_merged_session(
    parents: list[SessionEntry],
    new_session_id: str,
    now_iso_str: str,
) -> SessionEntry:
    """Compose a new SessionEntry from N parent sessions.

    Deterministic — no LLM. Union+dedupe fields, apply compaction thresholds,
    and build `compactedSummary` from each parent's digest. Parents are not
    modified.
    """
    if not parents:
        raise ValueError("merge requires at least one parent session")

    merged_files = _dedupe_preserve_order(
        [f for p in parents for f in p.filesChanged]
    )
    merged_decisions = _dedupe_preserve_order(
        [d for p in parents for d in p.decisions]
    )
    merged_learnings = _dedupe_preserve_order(
        [l for p in parents for l in p.learnings]
    )

    digest_sections = [_digest_parent(p) for p in parents]
    prior_compacted = [p.compactedSummary for p in parents if p.compactedSummary]
    compacted_parts = prior_compacted + digest_sections

    # If the merged decisions+learnings exceed the verbatim cap, push older
    # entries into `compactedSummary` and keep only the last few verbatim.
    entries_total = len(merged_decisions) + len(merged_learnings)
    compaction_count = sum(p.compactionCount for p in parents)
    if entries_total > COMPACT_ENTRIES_THRESHOLD:
        overflow = []
        if len(merged_decisions) > MERGE_VERBATIM_KEEP:
            overflow.append("older decisions dropped from verbatim: " +
                            "; ".join(merged_decisions[:-MERGE_VERBATIM_KEEP]))
            merged_decisions = merged_decisions[-MERGE_VERBATIM_KEEP:]
        if len(merged_learnings) > MERGE_VERBATIM_KEEP:
            overflow.append("older learnings dropped from verbatim: " +
                            "; ".join(merged_learnings[:-MERGE_VERBATIM_KEEP]))
            merged_learnings = merged_learnings[-MERGE_VERBATIM_KEEP:]
        compacted_parts.extend(overflow)
        compaction_count += 1

    if len(merged_files) > COMPACT_FILES_THRESHOLD:
        merged_files = merged_files[-COMPACT_FILES_THRESHOLD:]

    parent_ids = [p.sessionId for p in parents]
    summary = f"Merged from {len(parents)} session(s): " + ", ".join(parent_ids)

    return SessionEntry(
        sessionId=new_session_id,
        status="active",
        startedAt=now_iso_str,
        lastUpdatedAt=now_iso_str,
        summary=summary,
        filesChanged=merged_files,
        decisions=merged_decisions,
        learnings=merged_learnings,
        compactedSummary="\n\n---\n\n".join(compacted_parts),
        compactionCount=compaction_count,
        parents=parent_ids,
    )


def merge_sessions(
    project_dir: Path,
    parent_ids: list[str],
    new_session_id: str,
    now_iso_str: str,
    into_name: Optional[str] = None,
    dry_run: bool = False,
) -> tuple[SessionEntry, Optional[Path]]:
    """Load parents by ID, build a merged session, and (unless dry_run) persist.

    Returns (merged_entry, written_path). `written_path` is None when dry_run.
    Raises ValueError if any parent ID cannot be resolved.
    """
    parents: list[SessionEntry] = []
    missing: list[str] = []
    for pid in parent_ids:
        path = find_session_file(project_dir, pid)
        entry = load_session(path) if path else None
        if not entry:
            missing.append(pid)
        else:
            parents.append(entry)
    if missing:
        raise ValueError(f"Unknown session ID(s): {', '.join(missing)}")

    merged = build_merged_session(parents, new_session_id, now_iso_str)
    if dry_run:
        return merged, None

    target_dir = project_dir / "sessions" / (into_name or "_default")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{new_session_id}.json"
    _write_json(target_path, merged.model_dump())

    save_latest_session(project_dir, LatestSession(
        lastSessionId=new_session_id,
        lastUpdatedAt=now_iso_str,
        activeSession=into_name,
    ))
    return merged, target_path


def archive_closed_sessions(
    project_dir: Path,
    older_than_days: int = 7,
    now: Optional[datetime] = None,
) -> list[tuple[Path, Path, int, int]]:
    """Gzip closed sessions older than `older_than_days`.

    Returns a list of (original_path, archived_path, original_bytes, gzipped_bytes)
    tuples for each session archived. Sessions already gzipped, still active,
    or newer than the cutoff are skipped. Original files are removed after
    successful gzip write.
    """
    now = now or datetime.now(timezone.utc)
    archived: list[tuple[Path, Path, int, int]] = []
    sessions_dir = project_dir / "sessions"
    if not sessions_dir.exists():
        return archived

    for path in list(_iter_session_files(sessions_dir)):
        if path.suffix == ".gz":
            continue
        entry = load_session(path)
        if not entry or entry.status != "closed":
            continue

        # Prefer endedAt, fall back to lastUpdatedAt for the age check
        stamp = entry.endedAt or entry.lastUpdatedAt
        if stamp:
            try:
                dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if (now - dt).days < older_than_days:
                    continue
            except (ValueError, TypeError):
                # Unparseable timestamp — err on the side of archiving
                pass

        gz_path = path.with_suffix(path.suffix + ".gz")
        raw = path.read_bytes()
        gz_path.parent.mkdir(parents=True, exist_ok=True)
        gz_path.write_bytes(gzip.compress(raw))
        original_size = path.stat().st_size
        gz_size = gz_path.stat().st_size
        path.unlink()
        archived.append((path, gz_path, original_size, gz_size))

    return archived


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
    for path in _iter_session_files(project_dir / "sessions"):
        raw = _read_json(path)
        if not raw:
            continue
        file_id = _session_stem(path)
        session_id = raw.get("sessionId", "")
        if session_id and session_id != file_id:
            mismatched.append(
                f"file={file_id} != sessionId={session_id} in {path}"
            )

    return dangling, mismatched


def get_dir_size(path: Path) -> int:
    """Get total size of all files in a directory tree."""
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total
