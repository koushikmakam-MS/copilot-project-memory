# 📂 Copilot Project Memory

**Persistent, folder-scoped memory for GitHub Copilot CLI.**

One-time install. Works forever. Zero files in your repos.

---

## What It Does

Every time you open Copilot CLI in a project, it **remembers**:

| Feature | Example |
|---------|---------|
| 🔧 **Preferences** | "I use TypeScript, pnpm, Vitest, 2-space indent" |
| ✅ **Do's** | "Always use named exports" |
| ❌ **Don'ts** | "Never use `any` type" |
| 📦 **Project context** | Stack, key files, description |
| 🧩 **IDE extensions** | ESLint, Prettier, Tailwind IntelliSense |
| 📝 **Code snippets** | Reusable patterns saved per project |
| 🕐 **Sessions** | Resume where you left off or start fresh |
| 🌍 **Global rules** | Preferences that apply to ALL projects |

### How It Works

It's **not a code project** — it's a **prompt**. A single `copilot-instructions.md` file teaches Copilot the memory system. Copilot reads/writes YAML files in `~/.copilot/project-memory/` to persist memory across sessions.

---

## Install (One Time, Any Machine)

### Windows (PowerShell)
```powershell
# From a local clone:
.\install.ps1

# Or remote install:
irm https://raw.githubusercontent.com/koushikmakam-MS/copilot-project-memory/main/install.ps1 | iex
```

### macOS / Linux
```bash
# From a local clone:
bash install.sh

# Or remote install:
curl -fsSL https://raw.githubusercontent.com/koushikmakam-MS/copilot-project-memory/main/install.sh | bash
```

### What the installer does:
1. Creates `~/.copilot/project-memory/` with global and template folders
2. Installs the master prompt into `~/.copilot/copilot-instructions.md`
3. That's it. Open Copilot anywhere and it just works.

---

## Usage

### Automatic Behavior (no commands needed)

- **First time in a folder** → auto-detects your stack, creates project memory
- **Returning to a folder** → loads memory, offers to resume last session
- **Exit/end session** → auto-saves what happened (silent, no prompt)
- **Repeated corrections** → suggests saving as a rule after 2x

### Commands

All commands use the **`@memory` prefix** to avoid accidental triggers. Type them as regular chat messages.

#### Quick Commands
```
@memory remember Always use Zod for API validation     → ✅ Saved as a "do" rule
@memory remember Never use default exports              → ✅ Saved as a "don't" rule
@memory forget never-use-default-exports                → ✅ Rule removed
```

#### Memory Management
```
@memory status          — Overview of this project's memory
@memory prefs           — List preferences
@memory prefs set language typescript
@memory rules           — List all do's and don'ts
@memory add do rule: Use Zod for validation
@memory add dont rule: Never use any type
@memory context         — Show project context
@memory add next.js to stack
@memory add extension dbaeumer.vscode-eslint ESLint
@memory stats           — Stats across ALL projects
```

#### Snippets
```
@memory save snippet api-handler    — Save last code block as snippet
@memory get snippet api-handler     — Retrieve a snippet
@memory list snippets               — List all snippets
```

#### Team Sharing & Multi-Editor
```
@memory export team     — Generate .github/copilot-instructions.md for your team
@memory export editors  — Generate instruction files for VS Code, JetBrains, Neovim, Claude Code, Cursor
```

#### Backup & Restore
```
@memory backup          — Archive all memory to a file
@memory restore <path>  — Restore from backup
```

#### Reset
```
@memory reset           — Wipe this project's memory (asks confirmation)
```

---

## Storage Layout

```
~/.copilot/project-memory/
  ├── _global/                    # Your personal defaults (all projects)
  │   ├── preferences.yml
  │   ├── rules.yml
  │   └── snippets/
  ├── _template/                  # Template for new projects
  └── my-app-a3f2b1c8/           # Per-project memory
      ├── preferences.yml         # Project-specific preferences
      ├── rules.yml               # Do's and don'ts
      ├── context.yml             # Stack, key files, description
      ├── extensions.yml          # IDE extensions
      ├── sessions/               # Auto-saved session history
      └── snippets/               # Reusable code patterns
```

**Global vs Project:** When both define the same preference or conflicting rules, **project always wins**.

---

## Scope: Global Rules

Some rules should apply everywhere:
```
@memory add global do rule: I prefer concise answers
@memory add global dont rule: Never include unnecessary comments
```

These live in `_global/rules.yml` and are loaded for every project.

---

## Auto-Detection

On first open in a new folder, Copilot scans for:

| File | Detected As |
|------|------------|
| `package.json` | Node.js + framework (Next.js, React, Vue, etc.) |
| `requirements.txt` / `pyproject.toml` | Python + framework |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `pom.xml` / `build.gradle` | Java |
| `*.csproj` / `*.sln` | .NET |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `pubspec.yaml` | Dart/Flutter |

---

## FAQ

**Q: Does this add files to my repo?**
A: No. Everything lives in `~/.copilot/project-memory/`. Zero repo pollution.

**Q: Do I need Node.js or any runtime?**
A: No. It's just files + a prompt. No build step, no dependencies.

**Q: Can my team use this?**
A: Run `/memory export-team` to generate a `.github/copilot-instructions.md` that works for everyone — no install needed on their end.

**Q: How do I move to a new machine?**
A: Either run the installer again, or use `@memory backup` + `@memory restore`.

**Q: What if global and project rules conflict?**
A: Project rules always win.

---

## License

MIT
