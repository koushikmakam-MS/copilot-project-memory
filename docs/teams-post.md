# Teams Post — Pipeline Executor Announcement

Copy-paste this into Microsoft Teams. Uses Teams-compatible markdown and emoji.

---

## 🔄 NEW: Pipeline Executor for Copilot — No More Silent Step Skipping!

**The problem we all have:**
Ask Copilot to "set up the dev environment" → it does 5 of 8 steps and says "done" 🤦

**The fix:** Pipeline Executor Protocol — now built into Copilot Project Memory

---

### ⚡ 30-Second Summary

When Copilot detects a complex task, it now:

1️⃣ **Decomposes** into atomic steps with checks
2️⃣ **Shows you a visual workflow** and asks for approval
3️⃣ **Executes step-by-step** with evidence for every check
4️⃣ **Validates** independently — catches skipped steps
5️⃣ **Reports** a full audit trail

---

### 🎬 See It In Action

```
You: "Set up the project for a new developer"

🔄 Pipeline mode activated

═══ PIPELINE WORKFLOW ═══

  ┌──────────┐     ┌──────────┐
  │ 1. check │     │ 2. clone │
  │   python │     │   repo   │
  └────┬─────┘     └────┬─────┘
       └──────┬─────────┘
              ▼
       ┌────────────┐
       │ 3. install  │
       └──────┬─────┘
              ▼
       ┌────────────┐
       │ 4. test     │
       └────────────┘

  ⏳ Approve? → ✅ Yes

━━━ STEP [1/4]: check-python ━━━
📋 PRE-CHECK:  ✅
🔨 EXECUTE:    python --version → 3.11.9
📋 POST-CHECK: ✅ (evidence: Python 3.11.9)
🔍 VERIFY:     aipipeline verify --step check-python → ✅
📊 RESULT: ✅ PASSED

═══ FINAL REPORT ═══
  check-python   ✅   Python 3.11.9
  clone-repo     ✅   12 items
  install-deps   ✅   47 packages
  run-tests      ✅   18/18 passed
  Total: 4/4 ✅
═══════════════════
```

---

### 🛡️ Four Layers of Enforcement

| | Layer | What It Does |
|---|---|---|
| 📄 | **Stored Plan** | Plan saved to disk — AI reads from file, can't forget steps |
| 👤 | **User Approval** | You review the plan before anything runs |
| 🐍 | **Code Verify** | `aipipeline verify --step` after EACH step — Python checks, not AI |
| 🔍 | **AI Validator** | Independent agent checks: were ALL steps followed correctly? |

---

### 🚀 Get It Now

Already have copilot-project-memory?
```
cd copilot-project-memory && git pull && .\install.ps1 -Force
```

New user?
```
git clone https://github.com/koushikmakam-MS/copilot-project-memory.git
cd copilot-project-memory && .\install.ps1
```

---

### 📋 Quick Commands

| Command | What |
|---|---|
| `:pipeline <task>` | Run with verified execution |
| `:pipeline resume` | Resume interrupted pipeline |
| `:pipeline last` | Show last report |
| `:pipeline history` | Past runs |
| `:pipeline auto off` | Disable auto-detection |

---

### 💡 Key Points

✅ **Zero breaking changes** — existing users see no difference until they use `:pipeline`
✅ **Auto-detects** complex tasks (keywords: "set up", "deploy", "migrate", etc.)
✅ **Per-step code verification** — Python checks every postcondition, not just AI judgment
✅ **Crash-safe** — plan file tracks progress, `:pipeline resume` picks up
✅ **Extensible** — add tools to `tools/` directory, installer auto-discovers them
✅ **Open source** — contribute new tools with the [Tool Development Guide](docs/TOOL_DEVELOPMENT.md)

🔗 [PR #1](https://github.com/koushikmakam-MS/copilot-project-memory/pull/1) | 📂 [Repo](https://github.com/koushikmakam-MS/copilot-project-memory)

---

Try it and let me know what you think! 🎯

@Koushik
