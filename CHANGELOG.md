# Changelog

All notable changes to this project will be documented in this file.

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
