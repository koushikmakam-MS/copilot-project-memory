<#
.SYNOPSIS
  One-time installer for Copilot Project Memory skill.
  Run once on any machine — works forever after.

.DESCRIPTION
  Sets up:
  1. ~/.copilot/project-memory/ folder structure
  2. Global + project memory template files
  3. Master copilot-instructions.md that teaches Copilot the memory system

.EXAMPLE
  irm https://raw.githubusercontent.com/koushikmakam-MS/copilot-project-memory/main/install.ps1 | iex
#>

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$copilotDir = Join-Path $HOME ".copilot"
$memoryDir  = Join-Path $copilotDir "project-memory"
$globalDir  = Join-Path $memoryDir "_global"
$instructionsFile = Join-Path $copilotDir "copilot-instructions.md"

Write-Host ""
Write-Host "  📂 Copilot Project Memory — Installer" -ForegroundColor Cyan
Write-Host "  =======================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Create directory structure ---
Write-Host "  [1/4] Creating directory structure..." -ForegroundColor Yellow

$dirs = @(
    $memoryDir
    $globalDir
    (Join-Path $globalDir "sessions")
    (Join-Path $globalDir "snippets")
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "    ✅ Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "    ⏭️  Exists:  $dir" -ForegroundColor DarkGray
    }
}

# --- Step 2: Create global memory template files ---
Write-Host "  [2/4] Setting up global memory files..." -ForegroundColor Yellow

$globalPrefs = Join-Path $globalDir "preferences.yml"
if (-not (Test-Path $globalPrefs) -or $Force) {
    @"
# Global Preferences (apply to all projects unless overridden)
# These are YOUR personal defaults.

# language: typescript
# tone: concise
# style:
#   indent: 2
#   quotes: single
"@ | Set-Content -Path $globalPrefs -Encoding UTF8
    Write-Host "    ✅ Created: preferences.yml" -ForegroundColor Green
}

$globalRules = Join-Path $globalDir "rules.yml"
if (-not (Test-Path $globalRules) -or $Force) {
    @"
# Global Rules (apply to all projects unless overridden)
# Format:
#   - type: do|dont
#     description: "What to always/never do"
#     learned_from: "how this was learned"

rules: []
"@ | Set-Content -Path $globalRules -Encoding UTF8
    Write-Host "    ✅ Created: rules.yml" -ForegroundColor Green
}

$globalSnippets = Join-Path $globalDir "snippets" "README.md"
if (-not (Test-Path $globalSnippets) -or $Force) {
    @"
# Snippets
Save reusable code patterns here as `.md` files.
Each file should contain a code block and a short description.

Example: `api-handler.md`
"@ | Set-Content -Path $globalSnippets -Encoding UTF8
}

# --- Step 3: Create project memory template ---
Write-Host "  [3/4] Setting up project template..." -ForegroundColor Yellow

$templateDir = Join-Path $memoryDir "_template"
if (-not (Test-Path $templateDir)) {
    New-Item -ItemType Directory -Path $templateDir -Force | Out-Null
}

@"
# Project preferences (override global preferences)
# Uncomment and customize for this project.

# language: python
# framework: django
# package_manager: pip
# test_runner: pytest
# style:
#   indent: 4
#   quotes: double
"@ | Set-Content -Path (Join-Path $templateDir "preferences.yml") -Encoding UTF8

@"
# Project rules (in addition to global rules)
# Project rules win over global rules when they conflict.

rules: []
"@ | Set-Content -Path (Join-Path $templateDir "rules.yml") -Encoding UTF8

@"
# Project context — auto-detected on first open, editable anytime.
name: ""
description: ""
stack: []
key_files: []
notes: ""
"@ | Set-Content -Path (Join-Path $templateDir "context.yml") -Encoding UTF8

@"
# IDE Extensions for this project
# required: true means the extension is essential for this project

extensions: []
"@ | Set-Content -Path (Join-Path $templateDir "extensions.yml") -Encoding UTF8

Write-Host "    ✅ Created project template" -ForegroundColor Green

# --- Step 4: Install master instructions ---
Write-Host "  [4/4] Installing master instructions..." -ForegroundColor Yellow

$masterPrompt = Get-Content -Path (Join-Path $PSScriptRoot "copilot-instructions.md") -Raw -ErrorAction SilentlyContinue

if (-not $masterPrompt) {
    # Inline fallback — the full prompt is embedded here for standalone install
    $masterPrompt = @"

<!-- PROJECT MEMORY SKILL — Do not edit this section manually -->
<!-- Installed by copilot-project-memory. See: ~/.copilot/project-memory/ -->

## Project Memory System

You have access to a persistent project memory system stored at ~/.copilot/project-memory/.

### On Every Session Start
1. Determine the current working directory.
2. Check if a project memory folder exists for this directory in ~/.copilot/project-memory/.
   - The folder name is the project directory's leaf name + a short hash.
3. If memory exists:
   - Load preferences.yml, rules.yml, context.yml, extensions.yml
   - Also load global rules from ~/.copilot/project-memory/_global/
   - Check sessions/ for the last session summary
   - Tell the user: "📂 Found project memory for [name]. Resume last session or start fresh?"
4. If no memory exists:
   - Auto-detect the project stack by checking for package.json, requirements.txt, Cargo.toml, go.mod, pom.xml, etc.
   - Create a new project memory folder using the _template as a base
   - Tell the user: "📂 New project detected! I've auto-detected [stack]. I'll start learning your preferences."

### Conflict Resolution
- Project-level rules ALWAYS override global rules when they conflict.
- Project preferences override global preferences for the same key.

### Auto-Save on Exit
Before ending ANY session (when user says goodbye, exits, or conversation ends):
1. Write a session summary to the project's sessions/ folder as a JSON file
2. Include: what was discussed, files changed, decisions made, new learnings
3. Update sessions/latest.json to point to this session
4. This is AUTOMATIC — never ask the user, just do it silently

### When User Says "/remember" or "remember this"
- Parse the instruction and save it as a rule in the project's rules.yml
- If it starts with "never", "don't", "avoid", "no" → save as type: dont
- Otherwise → save as type: do
- Confirm: "✅ Remembered: [description]"

### When User Says "/forget"
- Remove the specified rule from rules.yml
- Confirm: "✅ Forgot: [rule]"

### When User Repeats a Correction 2+ Times
- Suggest: "I notice you've corrected this pattern before. Want me to remember this as a rule?"
- If yes, save to rules.yml with learned_from: "learned from repeated corrections"

### Commands
- /memory status — Show overview (preference count, rule count, extension count, session count)
- /memory prefs — List preferences; /memory prefs set <key> <value>; /memory prefs rm <key>
- /memory rules — List rules; /memory rules add-do <desc>; /memory rules add-dont <desc>; /memory rules rm <id>
- /memory context — Show context; /memory context set <field> <value>; /memory context stack <item>; /memory context keyfile <path>
- /memory extensions — List extensions; /memory extensions add <id> <name>; /memory extensions rm <id>
- /memory sessions — List sessions; /memory sessions last — show last session details
- /memory snippets — List saved snippets; /memory snippets save <name>; /memory snippets get <name>
- /memory export — Export full memory as a single markdown block
- /memory export-team — Export project rules as .github/copilot-instructions.md for team sharing
- /memory backup — Export all memory (global + all projects) as a single backup file
- /memory restore <path> — Restore memory from a backup file
- /memory reset — Wipe current project memory (asks for confirmation)
- /memory stats — Show detailed statistics across all projects
- /remember <instruction> — Quick-add a rule
- /forget <rule-id> — Remove a rule

### Snippet Library
Users can save reusable code patterns:
- /memory snippets save <name> — Save the last code block as a named snippet
- /memory snippets get <name> — Retrieve and display a snippet
- /memory snippets list — Show all snippets for this project
- Snippets are stored as markdown files in the project's snippets/ folder

### Team Sharing
- /memory export-team generates a clean .github/copilot-instructions.md
- It includes project context, rules, and preferences (not personal session history)
- Teammates get consistent Copilot behavior without installing this skill

### Backup & Restore
- /memory backup creates a single .tar.gz (or .zip on Windows) of ~/.copilot/project-memory/
- /memory restore <path> unpacks it back
- Useful for migrating to new machines beyond the installer

### Memory Stats
- /memory stats shows: total projects tracked, total rules, total sessions, most-used project, last accessed dates

<!-- END PROJECT MEMORY SKILL -->
"@
}

# Check if instructions file already exists and has memory skill
if (Test-Path $instructionsFile) {
    $existing = Get-Content -Path $instructionsFile -Raw
    if ($existing -match "PROJECT MEMORY SKILL") {
        if ($Force) {
            # Replace existing section
            $pattern = '(?s)<!-- PROJECT MEMORY SKILL.*?<!-- END PROJECT MEMORY SKILL -->'
            $updated = $existing -replace $pattern, $masterPrompt.Trim()
            Set-Content -Path $instructionsFile -Value $updated -Encoding UTF8
            Write-Host "    ✅ Updated master instructions (--Force)" -ForegroundColor Green
        } else {
            Write-Host "    ⏭️  Master instructions already installed. Use -Force to overwrite." -ForegroundColor DarkGray
        }
    } else {
        # Append to existing file
        Add-Content -Path $instructionsFile -Value "`n`n$masterPrompt" -Encoding UTF8
        Write-Host "    ✅ Appended to existing copilot-instructions.md" -ForegroundColor Green
    }
} else {
    Set-Content -Path $instructionsFile -Value $masterPrompt -Encoding UTF8
    Write-Host "    ✅ Created copilot-instructions.md" -ForegroundColor Green
}

Write-Host ""
Write-Host "  🎉 Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Memory location:  $memoryDir" -ForegroundColor White
Write-Host "  Instructions:     $instructionsFile" -ForegroundColor White

# --- Step 5: Set permanent permissions ---
Write-Host ""
Write-Host "  [Bonus] Setting permanent permissions..." -ForegroundColor Yellow

$configFile = Join-Path $copilotDir "config.json"
if (Test-Path $configFile) {
    try {
        $config = Get-Content $configFile -Raw | ConvertFrom-Json
        $memoryPath = $memoryDir.Replace('\', '\\')
        
        if (-not $config.trustedFolders) {
            $config | Add-Member -NotePropertyName "trustedFolders" -NotePropertyValue @()
        }
        
        $trustedList = [System.Collections.ArrayList]@($config.trustedFolders)
        if ($memoryDir -notin $trustedList) {
            $trustedList.Add($memoryDir) | Out-Null
            $config.trustedFolders = $trustedList.ToArray()
            $config | ConvertTo-Json -Depth 10 | Set-Content -Path $configFile -Encoding UTF8
            Write-Host "    ✅ Added project-memory to trusted folders" -ForegroundColor Green
        } else {
            Write-Host "    ⏭️  Already trusted" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host "    ⚠️  Could not update config.json (update manually with /add-dir)" -ForegroundColor Yellow
    }
}

$permissionsFile = Join-Path $copilotDir "permissions-config.json"
if (Test-Path $permissionsFile) {
    try {
        $perms = Get-Content $permissionsFile -Raw | ConvertFrom-Json
        if (-not $perms.locations.PSObject.Properties[$memoryDir]) {
            $perms.locations | Add-Member -NotePropertyName $memoryDir -NotePropertyValue @{
                tool_approvals = @(
                    @{ kind = "read" },
                    @{ kind = "write" }
                )
            }
            $perms | ConvertTo-Json -Depth 10 | Set-Content -Path $permissionsFile -Encoding UTF8
            Write-Host "    ✅ Added read/write permissions for project-memory" -ForegroundColor Green
        } else {
            Write-Host "    ⏭️  Permissions already set" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host "    ⚠️  Could not update permissions (Copilot will ask on first use)" -ForegroundColor Yellow
    }
} else {
    # Create permissions file
    @{
        locations = @{
            $memoryDir = @{
                tool_approvals = @(
                    @{ kind = "read" },
                    @{ kind = "write" }
                )
            }
        }
    } | ConvertTo-Json -Depth 10 | Set-Content -Path $permissionsFile -Encoding UTF8
    Write-Host "    ✅ Created permissions config" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Just open Copilot in any project folder — it will auto-detect" -ForegroundColor White
Write-Host "  and start building memory. No permission prompts, ever." -ForegroundColor White
Write-Host ""
