
<!-- PROJECT MEMORY SKILL — v2 (slim) -->
<!-- Simple ops: AI handles inline. Complex ops: use copilot-memory CLI. -->

## 🧠 Project Memory

You have persistent project memory at `~/.copilot/project-memory/`.
Files are YAML (rules.yml, preferences.yml, context.yml, tracking.yml) + JSON (sessions/).

### Loading Memory

**On first reply**, say: `💡 Project memory available — type :status to load, or :resume to pick up where you left off.`

**On `:status` or `:resume`**: run `copilot-memory status` to get the overview, then read the relevant YAML files.

### Commands (user types these as chat messages)

**Simple ops — handle inline** (read/write YAML files directly):

| User types | What to do |
|-----------|------------|
| `:status` | Run `copilot-memory status` and show the output |
| `:resume` | Read `sessions/latest.json` → load the session JSON it points to → show summary |
| `:remember <rule>` | Read `rules.yml` from the project memory folder, append a new rule to the `rules:` list (see YAML Write Rules below), write the file back. Confirm what was added. |
| `:forget <id>` | Read `rules.yml`, remove the rule with matching `id` from the `rules:` list, write the file back. Confirm what was removed. |
| `:rules` | Read `rules.yml` from the project memory folder and display the rules in a readable table |
| `:prefs` | Read `preferences.yml` from the project memory folder and display key-value pairs |
| `:prefs set <k> <v>` | Read `preferences.yml`, set/update the key under the appropriate section, write back |
| `:context` | Read `context.yml` from the project memory folder and display it |
| `:help` | Show command list |

**Finding the project memory folder:**
1. Get the git root folder name (e.g., `my-project`)
2. Lowercase it, replace underscores with hyphens
3. Look for `~/.copilot/project-memory/<name>/` (e.g., `~/.copilot/project-memory/my-project/`)
4. If it doesn't exist, run `copilot-memory init` first

**Complex ops — use `copilot-memory` CLI** (deterministic, validated):

| User types | Run this command |
|-----------|-----------------|
| `:verify` | `copilot-memory verify --fix` |
| `:compact` | `copilot-memory compact` |
| `:export team` | `copilot-memory export team` |
| `:init` | `copilot-memory init` |

### YAML Write Rules (when handling inline)

When writing YAML files, follow these exact patterns:

**Adding a rule** (`:remember never use any type`):
```yaml
# Append to the rules: list in rules.yml
- id: never-use-any-type          # lowercase, hyphens, max 50 chars, derived from the rule text
  type: dont                       # "do" if positive ("always X"), "dont" if negative ("never X")
  description: "never use any type"
  learned_from: "explicit instruction"
  created_at: "2026-06-11T12:00:00Z"
  last_used: "2026-06-11T12:00:00Z"
  use_count: 0
  share: false
```

**Removing a rule** (`:forget never-use-any-type`):
```yaml
# Read rules.yml, find the rule with id: never-use-any-type, remove it from the list, write back
```

**Setting a preference** (`:prefs set language python`):
```yaml
# In preferences.yml, under the appropriate section, set:
language: python
```

**Every YAML file MUST have** `schema_version: 1` as the first key. If missing, add it.

**Important:** Always read the full file first, modify in memory, then write the complete file back. Never partially write or append blindly.

### Session Auto-Save

After meaningful work (file edits, decisions, code generation), silently update or create
a session JSON in `sessions/_default/`:

```json
{
  "sessionId": "<uuid>",
  "status": "active",
  "startedAt": "<ISO>",
  "lastUpdatedAt": "<ISO>",
  "summary": "<1-line rolling summary>",
  "filesChanged": ["file1.ts", "file2.py"],
  "decisions": ["chose X over Y"],
  "learnings": ["user prefers Z"]
}
```

Update `sessions/latest.json` to point to the current session.

### Pipeline Mode

For multi-step tasks (3+ sequential steps), use the `pipeline` tool:
- Decompose into a plan YAML → save to `pipelines/active-plan.yaml`
- Execute with `pipeline run` and verify with `pipeline verify`
- See `pipeline --help` for details

<!-- END PROJECT MEMORY SKILL -->
