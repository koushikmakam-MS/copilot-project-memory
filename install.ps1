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

### When User Says ":remember"
- Parse the instruction and save it as a rule in the project's rules.yml
- If it starts with "never", "don't", "avoid", "no" → save as type: dont
- Otherwise → save as type: do
- Confirm: "✅ Remembered: [description]"

### When User Says ":forget"
- Remove the specified rule from rules.yml
- Confirm: "✅ Forgot: [rule]"

### When User Repeats a Correction 2+ Times
- Suggest: "I notice you've corrected this pattern before. Want me to remember this as a rule?"
- If yes, save to rules.yml with learned_from: "learned from repeated corrections"

### Commands (all use : prefix)
- :status — Show overview (preference count, rule count, extension count, session count)
- :prefs — List preferences; :prefs set <key> <value>; :prefs remove <key>
- :rules — List rules; :rules add do rule: <desc>; :rules add dont rule: <desc>; :rules remove <id>
- :context — Show context; :context set <field> <value>; :context stack <item>; :context keyfile <path>
- :extensions — List extensions; :extensions add <id> <name>; :extensions remove <id>
- :sessions — List sessions; :sessions last — show last session details
- :snippets — List snippets; :snippets save <name>; :snippets get <name>; :snippets delete <name>
- :export — Export full memory as a single markdown block
- :export team — Export project rules as .github/copilot-instructions.md for team sharing
- :export editors — Export instruction files for all supported editors
- :backup — Export all memory as a backup archive
- :restore <path> — Restore memory from a backup archive
- :reset — Wipe current project memory (asks for confirmation)
- :stats — Show detailed statistics across all projects
- :tracking — View auto-tracked behavioral patterns
- :remember <instruction> — Quick-add a rule
- :forget <rule-id> — Remove a rule
- :help — Show quick reference

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

# --- Step 5: Set up auto-permissions via shell alias ---
Write-Host ""
Write-Host "  [Bonus] Setting up auto-permissions..." -ForegroundColor Yellow

# Approach: Add a PowerShell function that wraps 'gh copilot' with --add-dir
# This ensures the memory path is ALWAYS in allowed directories, for ANY project.
$profilePath = $PROFILE.CurrentUserAllHosts
$aliasBlock = @"

# --- Copilot Project Memory: auto-grant memory path access ---
function Invoke-CopilotWithMemory {
    `$memDir = Join-Path `$HOME ".copilot" "project-memory"
    gh copilot -- --add-dir `$memDir @args
}
Set-Alias -Name ghc -Value Invoke-CopilotWithMemory -Scope Global
# --- End Copilot Project Memory ---
"@

try {
    if (-not (Test-Path $profilePath)) {
        New-Item -Path $profilePath -ItemType File -Force | Out-Null
    }
    $profileContent = Get-Content -Path $profilePath -Raw -ErrorAction SilentlyContinue
    if ($profileContent -and $profileContent -match "Copilot Project Memory") {
        Write-Host "    ⏭️  Shell alias already installed" -ForegroundColor DarkGray
    } else {
        Add-Content -Path $profilePath -Value $aliasBlock -Encoding UTF8
        Write-Host "    ✅ Added 'ghc' alias to PowerShell profile" -ForegroundColor Green
        Write-Host "       Use 'ghc' instead of 'gh copilot' for auto-permissions" -ForegroundColor White
    }
} catch {
    Write-Host "    ⚠️  Could not update profile — add manually:" -ForegroundColor Yellow
    Write-Host "       function ghc { gh copilot -- --add-dir `"$memoryDir`" @args }" -ForegroundColor White
}

# Also seed permissions-config.json for the current project (if run from a project dir)
$permFile = Join-Path $copilotDir "permissions-config.json"
try {
    $cwd = (Get-Location).Path
    # Skip if CWD is home or system dir
    if ($cwd -ne $HOME -and $cwd -ne "C:\") {
        $perms = @{ "locations" = @{} }
        if (Test-Path $permFile) {
            $perms = Get-Content $permFile -Raw | ConvertFrom-Json -AsHashtable
            if (-not $perms.locations) { $perms.locations = @{} }
        }
        
        # Find git root for locationKey
        $gitRoot = (git rev-parse --show-toplevel 2>$null)
        if ($gitRoot) {
            $locationKey = [System.IO.Path]::GetFullPath($gitRoot)
        } else {
            $locationKey = $cwd
        }
        
        if (-not $perms.locations[$locationKey]) {
            $perms.locations[$locationKey] = @{}
        }
        
        $loc = $perms.locations[$locationKey]
        $existingDirs = @()
        if ($loc["allowed_directories"]) { $existingDirs = @($loc["allowed_directories"]) }
        
        if ($memoryDir -notin $existingDirs) {
            $existingDirs += $memoryDir
            $loc["allowed_directories"] = $existingDirs
            if (-not $loc["tool_approvals"]) {
                $loc["tool_approvals"] = @(
                    @{ "kind" = "read" },
                    @{ "kind" = "write" }
                )
            }
            $perms | ConvertTo-Json -Depth 10 | Set-Content -Path $permFile -Encoding UTF8
            Write-Host "    ✅ Granted memory access for: $locationKey" -ForegroundColor Green
        } else {
            Write-Host "    ⏭️  Permissions already set for this project" -ForegroundColor DarkGray
        }
    }
} catch {
    Write-Host "    ⚠️  Could not update permissions-config.json" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  🎉 Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Two ways to use Copilot with project memory:" -ForegroundColor White
Write-Host "    1. Use 'ghc' (auto-grants memory access for any project)" -ForegroundColor White
Write-Host "    2. Use 'gh copilot' (memory access pre-granted for current project)" -ForegroundColor White
Write-Host ""
Write-Host "  💡 Re-run this installer from any project folder to grant access." -ForegroundColor DarkGray
Write-Host ""
