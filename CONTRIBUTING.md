# Contributing to Copilot Project Memory

Thanks for your interest in contributing! 🎉

This is a **prompt-only** system — no runtime, no dependencies, just structured text that teaches Copilot how to manage memory. That makes contributing easy: no build steps, no test suites, just edit and try it.

## How to Contribute

### 🐛 Report Issues
- Open an [issue](https://github.com/KoushikMakam/copilot-project-memory/issues) with a clear description
- Include your OS (Windows/macOS/Linux) and Copilot CLI version
- Include what you expected vs. what happened

### 💡 Suggest Features
- Open an issue with the `enhancement` label
- Describe the use case and expected behavior (example commands/output help!)

### 🔧 Pull Requests
1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test on your machine — run the installer, use the commands in Copilot CLI
5. Submit a PR with a clear description of what changed and why

### What to Contribute

| Area | Files | Ideas |
|------|-------|-------|
| **Core prompt** | `copilot-instructions.md` | New commands, behavior fixes, better detection |
| **Auto-tracking** | Prompt sections | New patterns to observe (refactoring habits, PR style) |
| **Editor support** | Export templates | Instruction file formats for new editors |
| **Installers** | `install.ps1`, `install.sh` | Cross-platform fixes, better error handling |
| **Metrics** | `scripts/collect-metrics.ps1` | Adoption tracking improvements |
| **Documentation** | `README.md`, this file | Usage examples, tutorials, clarity |

### Guidelines
- **Keep it prompt-only** — no runtime dependencies, no build steps, no package managers
- **Test your changes** — run the installer and verify commands work in Copilot CLI
- **One PR per feature/fix** — makes review easier
- Keep the prompt (`copilot-instructions.md`) focused and actionable

## Architecture

This project is intentionally simple:

```
copilot-instructions.md    → The system prompt (the entire "runtime")
install.ps1 / install.sh   → One-time setup scripts
~/.copilot/project-memory/  → Where memory lives (YAML + JSON files)
```

There's no code to compile, no tests to run. The "test" is: does it work correctly when you use it in Copilot CLI?

## Code of Conduct

Be respectful, constructive, and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
