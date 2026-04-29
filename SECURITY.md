# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT open a public issue** for security vulnerabilities
2. Email the maintainer or use [GitHub's private vulnerability reporting](https://github.com/koushikmakam-MS/copilot-project-memory/security/advisories/new)
3. Include a description of the vulnerability and steps to reproduce

## Security Considerations

### What This Project Stores

This skill stores data in `~/.copilot/project-memory/` on your local machine:
- Project preferences (language, framework, style)
- Rules (do's and don'ts)
- Project context (stack, key files)
- IDE extensions list
- Session summaries
- Behavioral tracking data

### Privacy by Design

- **All data is local** — nothing is sent to external servers by default
- **Sync is opt-in** — only if the user explicitly enables it
- **Team export excludes personal data** — session history, interaction style, and stats are never exported
- **No telemetry** — this skill does not collect or transmit any usage data

### Sensitive Data Warnings

- **Never store secrets** (API keys, tokens, passwords) in memory files
- **Review before sharing** — if you use `/memory export-team`, review the generated file before committing
- **Backup files** may contain personal session history — treat them as private

### Installer Safety

- The installer only creates files in `~/.copilot/` — it does not modify system files
- The installer does not require elevated/admin permissions
- The installer does not download or execute remote code (when run from a local clone)
- When using the remote install command (`curl | bash` or `irm | iex`), the script is fetched from this public GitHub repo

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | ✅        |
