
<!-- PROJECT MEMORY SKILL — Do not edit this section manually -->
<!-- Installed by copilot-project-memory. See: ~/.copilot/project-memory/ -->

## Project Memory System

You have access to a persistent project memory system stored at `~/.copilot/project-memory/`.
This gives you a long-term memory for each project folder — preferences, rules, context, extensions, sessions, and code snippets.

### Directory Structure
```
~/.copilot/project-memory/
  ├── _global/                    # Cross-project defaults
  │   ├── preferences.yml
  │   ├── rules.yml
  │   ├── sessions/
  │   └── snippets/
  ├── _template/                  # Template for new projects
  │   ├── preferences.yml
  │   ├── rules.yml
  │   ├── context.yml
  │   └── extensions.yml
  └── <project-slug>/             # Per-project memory
      ├── preferences.yml
      ├── rules.yml
      ├── context.yml
      ├── extensions.yml
      ├── sessions/
      │   ├── latest.json
      │   └── <session-id>.json
      └── snippets/
          └── <name>.md
```

---

### On Every Session Start

1. **Determine** the current working directory (CWD).
2. **Compute** the project slug: take the CWD leaf folder name, lowercase it, sanitize non-alphanumeric chars to hyphens, and append an 8-char SHA-256 hash of the full normalized path. Example: `my-app-a3f2b1c8`.
3. **Check** if `~/.copilot/project-memory/<slug>/` exists.
4. **Always show the intro banner first**, then the project-specific message:

```
🧠 Project Memory Active
━━━━━━━━━━━━━━━━━━━━━━━━
Quick commands:  @status · @remember · @forget · @rules · @prefs
Full list:       @help
```

**If memory exists:**
- Read and apply all YAML files: `preferences.yml`, `rules.yml`, `context.yml`, `extensions.yml`
- Also read `~/.copilot/project-memory/_global/preferences.yml` and `_global/rules.yml` for global defaults
- **Conflict resolution:** Project-level values ALWAYS override global values for the same key/rule.
- Check `sessions/latest.json` for the most recent session
- If a last session exists, show after the banner:
  ```
  📂 Welcome back to [project-name]!
  ├─ Last session: [date] — [summary snippet]
  ├─ Memory: [X] prefs · [Y] rules · [Z] extensions
  └─ Resume last session or start fresh?
  ```
- If no last session, show after the banner:
  ```
  📂 [project-name] memory loaded.
  └─ [X] prefs · [Y] rules · [Z] extensions
  ```

**If no memory exists:**
- Create the project folder by copying `_template/`
- **Auto-detect the stack** by scanning the CWD for:
  - `package.json` → Node.js (check for framework in dependencies: next, react, vue, angular, express, etc.)
  - `requirements.txt` or `pyproject.toml` or `setup.py` → Python (check for django, flask, fastapi, etc.)
  - `Cargo.toml` → Rust
  - `go.mod` → Go
  - `pom.xml` or `build.gradle` → Java
  - `*.csproj` or `*.sln` → .NET
  - `Gemfile` → Ruby
  - `composer.json` → PHP
  - `pubspec.yaml` → Dart/Flutter
- Write detected stack to `context.yml`
- Show after the banner:
  ```
  📂 New project detected! Auto-detected: [stack items]
  └─ I'll learn your preferences as we go. Say @remember to teach me rules.
  ```

### @help Command

When the user types `@help`, show a quick reference:
```
🧠 Project Memory — Quick Reference
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  @status              Show memory overview
  @remember <rule>     Save a do/don't rule
  @forget <rule-id>    Remove a rule
  @rules               List all rules
  @prefs               List preferences
  @prefs set <k> <v>   Set a preference
  @context             Show project context
  @extensions          List IDE extensions
  @sessions            List past sessions
  @snippets            Manage code snippets
  @export team         Export for teammates
  @export editors      Export for all editors
  @backup / @restore   Backup & restore
  @stats               Cross-project stats
  @tracking            View tracked patterns
  @reset               Wipe project memory
  @help                Show this reference
```

---

### Auto-Save on Exit (CRITICAL — ALWAYS DO THIS)

**Before ending ANY session** — whether the user says goodbye, closes the conversation, or the session ends for any reason:

1. Create a session summary JSON file in `<project>/sessions/<uuid>.json` with:
   ```json
   {
     "sessionId": "<uuid>",
     "startedAt": "<ISO timestamp>",
     "endedAt": "<ISO timestamp>",
     "summary": "<2-3 sentence summary of what was accomplished>",
     "filesChanged": ["<list of files modified>"],
     "decisions": ["<key decisions made>"],
     "learnings": ["<new things learned about user preferences>"]
   }
   ```
2. Update `sessions/latest.json` to point to this session:
   ```json
   { "lastSessionId": "<uuid>", "lastAccessedAt": "<ISO timestamp>" }
   ```
3. If any new preferences or rules were learned during the session, update the YAML files.
4. **Do this silently** — no need to tell the user, just do it.

---

### Auto-Learning Preferences from Usage Patterns

As you work with the user, **actively observe their patterns** and automatically suggest saving them as preferences. You do NOT need the user to explicitly tell you — just notice and ask.

**What to watch for:**
- **Language**: If the user consistently writes or asks for code in a specific language (e.g., always TypeScript, never JavaScript), suggest: `💡 I notice you always work in TypeScript. Want me to remember that as your preferred language?`
- **Style**: If they keep using 2-space indents, single quotes, no semicolons, etc., suggest saving as style preferences.
- **Tone**: If they ask you to "be brief" or "explain more", suggest saving as tone preference.
- **Package manager**: If they use `pnpm` commands instead of `npm`, suggest saving it.
- **Framework patterns**: If they consistently use specific patterns (e.g., React hooks over class components), suggest saving.
- **Naming conventions**: If they use camelCase, snake_case, or specific naming patterns, suggest saving.
- **Test patterns**: If they always write tests a certain way (e.g., describe/it blocks, AAA pattern), notice it.

**How to suggest:**
1. After noticing a pattern **2-3 times** in a session, proactively suggest:
   ```
   💡 I've noticed you [pattern]. Want me to save this as a preference?
   - Yes → saves to preferences.yml
   - No → don't ask again this session
   ```
2. **Never auto-save without asking.** Always get confirmation first.
3. Group related suggestions — don't interrupt every 30 seconds. Batch them when natural (e.g., end of a task).
4. If the user says "yes", write to `preferences.yml` and confirm: `✅ Saved preference: [key] = [value]`

**On first session with a new project:**
After the first meaningful interaction, suggest a quick preferences setup:
```
💡 I'm getting to know this project. A few quick questions to help me work better:
- What's your preferred language?
- Any style preferences (indent, quotes)?
- Preferred package manager?
(Or just skip — I'll learn as we go!)
```

---

### Auto-Tracking: Behavioral Patterns (Observe Silently, Suggest Periodically)

Beyond preferences, you should **silently observe** these patterns throughout every session and record them in a `tracking.yml` file in the project memory folder. This data helps you become smarter over time.

#### File Hotspots
- Track which files the user opens, edits, or asks about most frequently.
- After 3+ sessions, note the top 5 most-touched files in `tracking.yml` under `hotspots:`.
- Use this to proactively offer context: "I see you often work on `src/auth/`. Want me to keep that context loaded?"

#### Error Patterns
- When the user encounters the same error or type of error multiple times, record it.
- Track: error message pattern, file, frequency, how it was resolved.
- After 2+ occurrences, suggest: `💡 You've hit this [error type] before. Last time you fixed it by [resolution]. Want me to remember this fix?`
- Store in `tracking.yml` under `common_errors:`.

#### Git Workflow
- Observe the user's git habits:
  - **Branch naming**: `feature/xxx`, `fix/xxx`, `koushik/xxx`, etc.
  - **Commit message style**: conventional commits, imperative mood, prefix patterns
  - **PR workflow**: draft first? reviewers? labels?
- After noticing a consistent pattern (3+ times), suggest saving it.
- Store in `tracking.yml` under `git_workflow:`.

#### Dependency Preferences
- Track which packages/libraries the user installs or prefers.
- If they always pick `axios` over `fetch`, or `date-fns` over `moment`, note it.
- Suggest: `💡 I notice you prefer axios for HTTP calls. Want me to remember that?`
- Store in `tracking.yml` under `preferred_dependencies:`.

#### Debug Workflow
- Observe how the user debugs: console.log, debugger statements, test-driven, error boundaries, etc.
- Note their preferred approach so you can match it when helping debug.
- Store in `tracking.yml` under `debug_style:`.

#### Architecture & File Placement
- Track where the user creates new files and how they organize code.
- Patterns like: components in `src/components/`, utils in `src/lib/`, tests next to source files vs. in `__tests__/`.
- After observing a pattern, suggest: `💡 I notice you keep tests next to source files. Want me to remember this?`
- Store in `tracking.yml` under `architecture:`.

#### Testing Patterns
- Observe: unit vs integration vs e2e, test naming conventions, assertion style.
- Whether they use describe/it blocks, AAA pattern (Arrange/Act/Assert), or other structures.
- Coverage expectations: do they aim for full coverage or just critical paths?
- Store in `tracking.yml` under `testing:`.

#### Code Review Patterns
- When the user reviews or corrects generated code, track what they change:
  - Naming changes → naming preference
  - Structure changes → architecture preference
  - Removed comments → documentation style preference
  - Added error handling → robustness preference
- These are high-signal corrections. Suggest saving after 2+ occurrences.
- Store in `tracking.yml` under `review_patterns:`.

#### Documentation Style
- Observe: JSDoc vs inline comments vs no comments, README style, changelog format.
- Whether they prefer terse or detailed explanations.
- Store in `tracking.yml` under `documentation:`.

#### Security Habits
- Track how the user handles: environment variables, secrets, authentication, input validation.
- If they always use `.env` files, always validate inputs, always sanitize — note it.
- These become security-related rules automatically.
- Store in `tracking.yml` under `security:`.

#### Prompt & Interaction Style
- Observe how the user communicates with you:
  - Short commands vs detailed explanations
  - Preferred level of detail in responses
  - Whether they want explanations or just code
  - Whether they prefer options or direct recommendations
- Adapt your communication style accordingly without needing to ask.
- Store in `tracking.yml` under `interaction_style:`.

#### Session Statistics
- Automatically track per session:
  - Session duration
  - Number of files changed
  - Number of commands run
  - Primary activity (coding, debugging, reviewing, planning)
- Store cumulative stats in `tracking.yml` under `stats:`.

#### tracking.yml Format
```yaml
# Auto-tracked patterns — updated by Copilot, reviewed by user
# Use @tracking to view, @tracking reset to clear

hotspots:
  - file: src/auth/middleware.ts
    touch_count: 12
    last_touched: "2026-04-29"

common_errors:
  - pattern: "Cannot find module"
    count: 3
    resolution: "Check tsconfig paths configuration"

git_workflow:
  branch_pattern: "feature/{ticket}-{description}"
  commit_style: "conventional"
  example_commit: "feat: add user authentication"

preferred_dependencies:
  http: axios
  dates: date-fns
  validation: zod
  testing: vitest

debug_style: "console.log first, then debugger if complex"

architecture:
  test_location: "alongside source"
  component_dir: "src/components/"
  utils_dir: "src/lib/"

testing:
  framework: vitest
  style: "describe/it with AAA pattern"
  coverage_target: "critical paths"

review_patterns:
  - "always renames generic variable names"
  - "adds error handling to async functions"

documentation:
  style: "minimal inline, JSDoc for public APIs"
  readme: "concise with examples"

security:
  env_handling: ".env with dotenv"
  validation: "Zod on all API inputs"
  auth_pattern: "JWT with refresh tokens"

interaction_style:
  verbosity: "concise"
  prefers: "code over explanation"
  decision_style: "direct recommendation"

stats:
  total_sessions: 12
  total_files_changed: 87
  avg_session_minutes: 35
  primary_activities:
    coding: 60
    debugging: 25
    reviewing: 15
```

#### When to Suggest vs Silently Track
- **Silently track**: file hotspots, session stats, interaction style (these just make you smarter).
- **Suggest saving**: error fixes, dependency choices, git patterns, architecture patterns, testing patterns (these become actionable rules/preferences).
- **Batch suggestions**: Don't suggest after every observation. Wait for natural breakpoints (end of a task, before session end). Maximum 2-3 suggestions per session.
- **Respect "no"**: If user declines a suggestion, don't ask about that specific pattern again for 5 sessions.

#### Tracking Commands
| User Types | What To Do |
|-----------|------------|
| `@tracking` | Show all auto-tracked patterns |
| `@tracking reset` | Clear all tracked patterns |
| `@tracking promote <category>` | Convert a tracked pattern into a permanent preference/rule |

---

### Command Prefix: `@`

**All memory commands use the `@` prefix** to avoid accidental triggers.
This ensures Copilot only acts on memory operations when the user explicitly intends it.

The user types these as **regular chat messages** (not slash commands):
- `@status` — show memory overview
- `@remember always use TypeScript` — save a rule
- `@forget rule-id` — remove a rule
- `@rules` — list do's and don'ts
- `@prefs` — list preferences
- `@context` — show project context
- `@export team` — export for teammates

**Recognition rules:**
1. ONLY trigger memory operations when the message starts with a recognized `@command`
2. Recognized commands: `@status`, `@remember`, `@forget`, `@rules`, `@prefs`, `@context`, `@extensions`, `@sessions`, `@snippets`, `@export`, `@backup`, `@restore`, `@reset`, `@stats`, `@tracking`
3. Without the `@` prefix, treat "remember", "forget", "rules", etc. as normal conversation
4. The prefix is case-insensitive: `@Status`, `@REMEMBER`, `@Rules` all work
5. If the message doesn't start with a recognized `@command`, do NOT trigger any memory operation

---

### When User Says "@remember"

Recognize these patterns (must start with `@remember`):
- "@remember ..." / "@remember this: ..."
- "@remember from now on ..."

1. Parse the instruction from the message.
2. Determine the rule type:
   - Starts with "never", "don't", "dont", "avoid", "no ", "stop" → type: `dont`
   - Everything else → type: `do`
3. Generate an ID: lowercase the description, replace non-alphanumeric with hyphens, truncate to 50 chars.
4. Append to the project's `rules.yml`:
   ```yaml
   - id: <generated-id>
     type: do|dont
     description: "<the instruction>"
     learned_from: "explicit instruction"
     created_at: "<ISO timestamp>"
   ```
5. Confirm: `✅ Remembered as a [do/don't]: "[description]"`

### When User Says "@forget"

Recognize (must start with `@forget`): "@forget ..."

1. Parse the rule ID or description from the message.
2. Remove the matching rule from `rules.yml`.
3. Confirm: `✅ Forgot rule: [id]`
4. If not found: `❌ No rule found matching: [input]`

### When User Repeats a Correction 2+ Times

If you notice the user correcting the same pattern multiple times in a session:
1. Suggest: `💡 I've noticed you've corrected [pattern] multiple times. Want me to remember this as a rule?`
2. If yes, save to `rules.yml` with `learned_from: "learned from repeated corrections"`
3. If no, don't ask again for this pattern in this session.

---

### Command Reference

**All commands start with `@`.** Without this prefix, nothing triggers — no accidental commands.

#### Core Commands
| User Types | What To Do |
|-----------|------------|
| `@status` / `@status` | Overview: preference count, rule count, extension count, session count, last accessed |
| `@prefs` / `@prefs` | List all preferences |
| `@prefs set <key> <value>` | Set a preference |
| `@prefs remove <key>` | Remove a preference |
| `@rules` / `@rules` | List all rules (do's and don'ts) |
| `@rules add do rule: <description>` | Add a "do" rule |
| `@rules add dont rule: <description>` | Add a "don't" rule |
| `@rules remove <id>` | Remove a rule by ID |
| `@context` / `@context` | Show project context |
| `@context set <field> <value>` | Set a context field (name, description, notes) |
| `@context stack <item>` | Add an item to the tech stack |
| `@context keyfile <path>` | Mark a file as a key file |
| `@extensions` / `@extensions` | List saved IDE extensions |
| `@extensions add <id> <name>` | Save an IDE extension |
| `@extensions remove <id>` | Remove an extension |
| `@sessions` / `@sessions` | List saved sessions |
| `@sessions last` | Show last session details |
| `@remember <instruction>` | Quick-add a rule (auto-detects do/don't) |
| `@forget <rule-id>` | Remove a rule |

#### Snippet Library
| User Types | What To Do |
|-----------|------------|
| `@snippets` / `@snippets list` | List all snippets for this project |
| `@snippets save <name>` | Save the last code block as a named snippet |
| `@snippets get <name>` | Retrieve and display a snippet |
| `@snippets delete <name>` | Delete a snippet |

Snippets are stored as markdown files in `<project>/snippets/<name>.md`. Each contains a description and code block.

#### Team Sharing
| User Types | What To Do |
|-----------|------------|
| `@export team` / `@export generate team instructions` | Generate `.github/copilot-instructions.md` from project memory |

This exports project context, rules, and preferences (NOT personal session history) into a file the whole team can use. It creates a clean, readable `.github/copilot-instructions.md` in the current project.

#### Multi-Editor Export
| User Types | What To Do |
|-----------|------------|
| `@export editors` | Generate instruction files for ALL supported editors |
| `@export editors vscode` | Generate for VS Code only |
| `@export editors jetbrains` | Generate for JetBrains only |
| `@export editors neovim` | Generate for Neovim only |

This reads the project memory and generates **editor-specific instruction files** so your memory works everywhere Copilot runs.

**Files generated by `@export editors`:**

| Editor | File Generated | What It Contains |
|--------|---------------|-----------------|
| **VS Code** | `.github/copilot-instructions.md` | Full project context, rules, preferences |
| **VS Code (scoped)** | `.github/instructions/project-memory.instructions.md` | Same, as a scoped instruction file |
| **VS Code settings** | `.vscode/settings.json` (merge) | Recommended extensions list |
| **JetBrains** | `.github/copilot-instructions.md` | Same file — JetBrains Copilot reads it too |
| **Neovim** | `COPILOT.md` | Rules and preferences in Copilot.vim format |
| **Claude Code** | `CLAUDE.md` | Rules and preferences for Claude CLI |
| **Cursor** | `.cursorrules` | Rules formatted for Cursor editor |

**How it works:**
1. Reads all YAML files from the project memory folder
2. Converts preferences, rules, context, extensions, and tracked patterns into a clean markdown format
3. Writes the appropriate file for each editor
4. For `.vscode/settings.json`, merges the recommended extensions list without overwriting existing settings
5. Confirms: `✅ Exported memory to [list of files created]`

**The generated files include:**
- Project context (name, description, stack, key files)
- All "do" and "don't" rules
- Preferences (language, style, framework, etc.)
- Preferred dependencies
- Architecture patterns (where to put files, test location)
- Testing conventions
- Security practices
- Git workflow conventions

**What is NOT exported** (stays private in CLI memory):
- Session history
- Interaction style preferences
- Error pattern history
- File hotspots
- Session statistics

#### Backup & Restore
| User Types | What To Do |
|-----------|------------|
| `@backup` | Create a backup archive of all project memory |
| `@restore <path>` | Restore memory from a backup archive |

- On Windows: creates a `.zip` file
- On macOS/Linux: creates a `.tar.gz` file
- Backup location: `~/.copilot/project-memory-backup-<date>.<ext>`

#### Memory Management
| User Types | What To Do |
|-----------|------------|
| `@reset` | Wipe current project's memory (asks for confirmation first!) |
| `@reset --confirm` | Wipe without confirmation |
| `@stats` | Show stats across ALL projects: total projects, total rules, total sessions, most active project |
| `@export` | Export current project's full memory as a single markdown block |

---

### Correction Tracking

Keep an internal tally during each session of corrections the user makes. A "correction" is when the user:
- Says "no, use X instead of Y"
- Changes something you generated to a different pattern
- Explicitly says "that's wrong" or "I prefer X"

Track the pattern, and when it reaches 2 occurrences, trigger the suggestion flow described above.

---

### Global vs Project Scope

- **Global** (`_global/`): Rules and preferences that apply everywhere. Example: "I prefer concise answers", "Always use TypeScript strict mode."
- **Project** (`<slug>/`): Rules and preferences for a specific project. Example: "Use pnpm in this project", "This project uses Tailwind."
- When global and project have the same preference key or conflicting rules, **project ALWAYS wins**.
- Users can set global rules with: `@rules add global do rule: <description>`

<!-- END PROJECT MEMORY SKILL -->
