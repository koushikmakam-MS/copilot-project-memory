
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
| `:resume` | Read `sessions/latest.json` → load the last session JSON → show summary |
| `:remember <rule>` | Append to `rules.yml` with auto-detected type (do/dont) and generated ID. Confirm. |
| `:forget <id>` | Remove rule from `rules.yml` by ID. Confirm. |
| `:rules` | Read and display `rules.yml` |
| `:prefs` | Read and display `preferences.yml` |
| `:prefs set <k> <v>` | Set key in `preferences.yml` |
| `:context` | Read and display `context.yml` |
| `:help` | Show command list |

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
# Append to rules: list in rules.yml
- id: never-use-any-type          # lowercase, hyphens, max 50 chars
  type: dont                       # "do" or "dont" (auto-detect from text)
  description: "never use any type"
  learned_from: "explicit instruction"
  created_at: "2026-06-11T12:00:00Z"
  last_used: "2026-06-11T12:00:00Z"
  use_count: 0
  share: false
```

**Every YAML file MUST have** `schema_version: 1` as the first key. If missing, add it.

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

### Project Folder Matching

To find the memory folder: get the git root leaf name, lowercase it, replace underscores
with hyphens, and look for a folder starting with that prefix in `~/.copilot/project-memory/`.
If none exists, run `copilot-memory init`.

<!-- END PROJECT MEMORY SKILL -->
