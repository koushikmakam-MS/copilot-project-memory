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
  irm https://raw.githubusercontent.com/KoushikMakam/copilot-project-memory/main/install.ps1 | iex
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
if (-not (Test-Path $globalPrefs)) {
    @"
schema_version: 1

# Global Preferences (apply to all projects unless overridden)
# These are YOUR personal defaults.

# language: typescript
# tone: concise
# style:
#   indent: 2
#   quotes: single
"@ | Set-Content -Path $globalPrefs -Encoding UTF8
    Write-Host "    ✅ Created: preferences.yml" -ForegroundColor Green
} elseif ($Force) {
    Copy-Item $globalPrefs "$globalPrefs.bak" -Force
    Write-Host "    ⏭️  Backed up existing preferences.yml → preferences.yml.bak" -ForegroundColor DarkGray
}

$globalRules = Join-Path $globalDir "rules.yml"
if (-not (Test-Path $globalRules)) {
    @"
schema_version: 1

# Global Rules (apply to all projects unless overridden)
# Format:
#   - type: do|dont
#     description: "What to always/never do"
#     learned_from: "how this was learned"

rules: []
"@ | Set-Content -Path $globalRules -Encoding UTF8
    Write-Host "    ✅ Created: rules.yml" -ForegroundColor Green
} elseif ($Force) {
    Copy-Item $globalRules "$globalRules.bak" -Force
    Write-Host "    ⏭️  Backed up existing rules.yml → rules.yml.bak" -ForegroundColor DarkGray
}

$globalSnippets = Join-Path (Join-Path $globalDir "snippets") "README.md"
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
schema_version: 1

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
schema_version: 1

# Project rules (in addition to global rules)
# Project rules win over global rules when they conflict.

rules: []
"@ | Set-Content -Path (Join-Path $templateDir "rules.yml") -Encoding UTF8

@"
schema_version: 1

# Project context — auto-detected on first open, editable anytime.
name: ""
description: ""
stack: []
key_files: []
notes: ""
"@ | Set-Content -Path (Join-Path $templateDir "context.yml") -Encoding UTF8

@"
schema_version: 1

# IDE Extensions for this project
# required: true means the extension is essential for this project

extensions: []
"@ | Set-Content -Path (Join-Path $templateDir "extensions.yml") -Encoding UTF8

Write-Host "    ✅ Created project template" -ForegroundColor Green

# --- Step 4: Install master instructions ---
Write-Host "  [4/6] Installing master instructions..." -ForegroundColor Yellow

# Prefer the slim v2 prompt if available, fall back to legacy
$masterPromptPath = Join-Path $PSScriptRoot "prompts" "copilot-instructions-slim.md"
if (-not (Test-Path $masterPromptPath)) {
    $masterPromptPath = Join-Path $PSScriptRoot "copilot-instructions.md"
}
$masterPrompt = Get-Content -Path $masterPromptPath -Raw -ErrorAction SilentlyContinue

if (-not $masterPrompt) {
    Write-Host "    !! No instructions file found in $PSScriptRoot" -ForegroundColor Red
    Write-Host "       Run installer from the copilot-project-memory repo directory." -ForegroundColor White
    exit 1
}
Write-Host "    Using: $(Split-Path $masterPromptPath -Leaf)" -ForegroundColor DarkGray

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

# --- Step 5: Install bundled tools ---
Write-Host "  [5/6] Installing bundled tools..." -ForegroundColor Yellow

$toolsDir = Join-Path $PSScriptRoot "tools"
if (Test-Path $toolsDir) {
    $toolDirs = Get-ChildItem -Path $toolsDir -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName "pyproject.toml")
    }
    if ($toolDirs.Count -eq 0) {
        Write-Host "    -- No tools found in tools/" -ForegroundColor DarkGray
    }
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    foreach ($tool in $toolDirs) {
        $toolName = $tool.Name
        Write-Host "    Installing $toolName..." -ForegroundColor White -NoNewline
        try {
            $pipResult = python -m pip install $tool.FullName 2>&1 | Out-String
            if ($pipResult -match "Successfully installed" -or $pipResult -match "already satisfied") {
                Write-Host " OK" -ForegroundColor Green
            } else {
                Write-Host " WARN (check: pip install $($tool.FullName))" -ForegroundColor Yellow
            }
        } catch {
            Write-Host " FAILED (Python/pip required)" -ForegroundColor Yellow
        }
    }
    # Whitelist installed tool executables with Windows Defender Controlled Folder Access
    Write-Host ""
    Write-Host "  [5b] Checking Windows Defender Controlled Folder Access..." -ForegroundColor Yellow

    $cfaEnabled = $false
    try {
        $cfaStatus = (Get-MpPreference).EnableControlledFolderAccess
        $cfaEnabled = ($cfaStatus -eq 1 -or $cfaStatus -eq "Enabled")
    } catch {
        # Get-MpPreference not available (e.g., Windows Server Core)
    }

    if ($cfaEnabled) {
        foreach ($tool in $toolDirs) {
            $toolName = $tool.Name
            # Find the installed exe in Python Scripts
            $pythonScripts = Join-Path (Split-Path (Get-Command python -ErrorAction SilentlyContinue).Source) "Scripts"
            $exePath = Join-Path $pythonScripts "$toolName.exe"

            if (Test-Path $exePath) {
                try {
                    $allowed = (Get-MpPreference).ControlledFolderAccessAllowedApplications
                    if ($allowed -and ($allowed -contains $exePath)) {
                        Write-Host "    ⏭️  $toolName.exe already whitelisted" -ForegroundColor DarkGray
                    } else {
                        Add-MpPreference -ControlledFolderAccessAllowedApplications $exePath
                        Write-Host "    ✅ Whitelisted $exePath in Controlled Folder Access" -ForegroundColor Green
                    }
                } catch {
                    Write-Host "    ⚠️  Could not whitelist $toolName.exe — run as Admin or whitelist manually:" -ForegroundColor Yellow
                    Write-Host "       Windows Security → Virus & threat protection → Ransomware protection" -ForegroundColor White
                    Write-Host "       → Allow an app through Controlled folder access → Add: $exePath" -ForegroundColor White
                }
            }
        }
    } else {
        Write-Host "    ⏭️  Controlled Folder Access not enabled — no whitelist needed" -ForegroundColor DarkGray
    }

    $ErrorActionPreference = $oldEAP
} else {
    Write-Host "    -- No tools/ directory found" -ForegroundColor DarkGray
}

# --- Step 6: Set up auto-permissions via shell alias ---
Write-Host ""
Write-Host "  [6/6] Setting up shell integration..." -ForegroundColor Yellow

# Add a PowerShell alias that ensures memory path is accessible.
# We pre-seed permissions-config.json (Step 6b below) so `gh copilot` already
# has access. The alias is just a convenience shortcut.
$profilePath = $PROFILE.CurrentUserAllHosts
$aliasBlock = @"

# --- Copilot Project Memory: convenience alias ---
function Invoke-CopilotWithMemory {
    gh copilot @args
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
    Write-Host "       Set-Alias -Name ghc -Value { gh copilot @args } -Scope Global" -ForegroundColor White
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

# --- Post-install verification ---
Write-Host "  Verifying installation..." -ForegroundColor Yellow

$verifyPassed = $true

# Check directory structure
if (Test-Path $memoryDir) {
    Write-Host "    ✅ Memory directory exists" -ForegroundColor Green
} else {
    Write-Host "    ❌ Memory directory missing: $memoryDir" -ForegroundColor Red
    $verifyPassed = $false
}

# Check instructions file
if ((Test-Path $instructionsFile) -and (Select-String -Path $instructionsFile -Pattern "PROJECT MEMORY SKILL" -Quiet)) {
    Write-Host "    ✅ Instructions file installed" -ForegroundColor Green
} else {
    Write-Host "    ❌ Instructions file missing or incomplete" -ForegroundColor Red
    $verifyPassed = $false
}

# Check CLI tools
try {
    $null = Get-Command copilot-memory -ErrorAction Stop
    Write-Host "    ✅ copilot-memory CLI available" -ForegroundColor Green
} catch {
    Write-Host "    ⚠️  copilot-memory CLI not found (Python tools optional)" -ForegroundColor Yellow
}

try {
    $null = Get-Command pipeline -ErrorAction Stop
    Write-Host "    ✅ pipeline CLI available" -ForegroundColor Green
} catch {
    Write-Host "    ⚠️  pipeline CLI not found (Python tools optional)" -ForegroundColor Yellow
}

if ($verifyPassed) {
    Write-Host ""
    Write-Host "  ✅ All checks passed!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  ⚠️  Some checks failed — review the output above" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Two ways to use Copilot with project memory:" -ForegroundColor White
Write-Host "    1. Use 'ghc' (auto-grants memory access for any project)" -ForegroundColor White
Write-Host "    2. Use 'gh copilot' (memory access pre-granted for current project)" -ForegroundColor White
Write-Host ""
Write-Host "  💡 Re-run this installer from any project folder to grant access." -ForegroundColor DarkGray
Write-Host ""
