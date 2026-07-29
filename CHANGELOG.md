# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-07-29

### Added
- 🗜️ **Session auto-compaction on save** — When a session crosses any threshold (decisions+learnings > 20, filesChanged > 30, or serialized size > 8 KB), older entries are collapsed into a new `compactedSummary` field before writing. Only the last 5 decisions/learnings are kept verbatim. Massively reduces token cost on `:resume`.
  - New `SessionEntry` fields: `compactedSummary: str`, `compactionCount: int`.
  - New CLI: `copilot-memory session check-size [--path P | --session-id ID]` — deterministic gate (exit 1 = compact recommended).
  - `:status` now shows `🗜️ Compactions: N` and warns when the latest session is ready to compact.
- 📦 **Gzip archival for cold sessions** — `copilot-memory compact` now automatically gzips closed sessions older than 7 days into `<sid>.json.gz`. Reads are transparent — `load_session`, `find_session_file`, `list_sessions`, and integrity checks all handle both extensions. Also exposed as `copilot-memory session archive [--older-than-days N]`.
- 🔀 **Session merging** — Combine multiple past sessions into a new session that inherits their union of context. Chat command `:merge <sid1> <sid2> [into <name>]`; CLI `copilot-memory session merge <sids...> [--into NAME] [--new-id ID] [--dry-run]`.
  - New `SessionEntry.parents: list[str]` for lineage.
  - Deduplicated union of `filesChanged` / `decisions` / `learnings`; overflow beyond compaction thresholds is folded into `compactedSummary` with per-parent digests.
  - Parents are **never mutated** — original sessions remain resumable individually.

### Changed
- `copilot-memory compact` runs archival before size-cap enforcement, and cap counting now covers both `.json` and `.json.gz` entries so limits stay accurate after archival.
- Test suite grew from 56 → 81 (25 new tests across compaction, archival, and merge).

## [1.1.0] - 2026-04-30

### Added
- 🧹 **Storage caps & eviction** — Hard caps on sessions (10 default, 20 per named), tracking entries (5 hotspots, 10 errors). Enforced on auto-save and via `:compact`.
- 📊 **Staleness metadata** — Rules gain `last_used`, `use_count`, and `share` fields (best-effort tracking).
- 🔍 **`:verify` command** — Non-destructive integrity check of all memory files. Recreates missing files from template, reports corruption without overwriting.
- 🧹 **`:compact` command** — Prunes stale derived data, enforces storage caps, suggests (never auto-deletes) stale explicit rules.
- 📌 **`:rules touch <id>`** — Mark a rule as still relevant to prevent staleness warnings.
- 🎯 **Selective team export** — Only rules with `share: true` are exported by default. New flags: `--scope`, `--fresh`, `--max-size`, `--all-rules`.
- ⚡ **Contextual loading** — Only loads what's needed: prefs/rules/context/latest.json always; tracking/sessions/snippets on demand.
- 📋 **Schema versioning** — All YAML files include `schema_version: 1` header for forward compatibility.
- 🤝 **Share prompt on `:remember`** — Users are asked if new rules should be shared with teammates.

### Changed
- Team export uses deterministic priority order (context → don'ts → do's → architecture → testing → security → deps → git)
- `:help` menu updated with new commands

## [1.0.0] - 2026-04-29

### Added
- 📂 **Core memory system** — preferences, rules (do's/don'ts), project context, IDE extensions, sessions
- 🔍 **Auto-detection** — automatically detects project stack from package.json, requirements.txt, Cargo.toml, etc.
- 💡 **Auto-learning** — observes user patterns and suggests saving as preferences after 2-3 occurrences
- 📊 **Behavioral tracking** — silently tracks file hotspots, error patterns, git workflow, dependency choices, debug style, architecture, testing patterns, code review patterns, documentation style, security habits, interaction style, and session stats
- 🔄 **Session management** — auto-saves on exit, resume or start fresh on next open
- 🌍 **Global + project scoping** — global rules apply everywhere, project rules override when they conflict
- 🧩 **IDE extensions tracking** — save and manage extensions per project
- 📝 **Snippet library** — save and retrieve reusable code patterns
- 👥 **Team sharing** — `/memory export-team` generates `.github/copilot-instructions.md` for the whole team
- 🖥️ **Multi-editor export** — `/memory export-editors` generates instruction files for VS Code, JetBrains, Neovim, Claude Code, and Cursor
- 💾 **Backup & restore** — archive all memory for machine migration
- 🛠️ **One-time installer** — PowerShell (Windows) and Bash (macOS/Linux) scripts
- 📋 **Full command set** — `/memory`, `/remember`, `/forget`, and all subcommands
