<#
.SYNOPSIS
  Whitelist copilot-memory tools with Windows Defender Controlled Folder Access.
  MUST be run as Administrator (right-click PowerShell → Run as administrator).
#>

$ErrorActionPreference = "Stop"

$pythonBase = (Get-Command python -ErrorAction SilentlyContinue).Source | Split-Path
if (-not $pythonBase) { $pythonBase = "$env:LOCALAPPDATA\Programs\Python\Python311" }
$scriptsDir = Join-Path $pythonBase "Scripts"

$tools = @(
    # Python and CLI tools
    (Join-Path $pythonBase "python.exe"),
    (Join-Path $scriptsDir "aipipeline.exe"),
    (Join-Path $scriptsDir "copilot-memory.exe"),
    # Terminal hosts (CFA blocks these when CLI writes to protected dirs)
    "C:\Windows\System32\conhost.exe",
    "C:\Windows\System32\cmd.exe"
)

# Also find Windows Terminal executables
$wtPaths = Get-ChildItem "C:\Program Files\WindowsApps\Microsoft.WindowsTerminal*" -Directory -ErrorAction SilentlyContinue
foreach ($wt in $wtPaths) {
    $exes = Get-ChildItem $wt.FullName -Filter "*.exe" -ErrorAction SilentlyContinue
    foreach ($exe in $exes) { $tools += $exe.FullName }
}

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "   Right-click PowerShell → Run as administrator → re-run this script" -ForegroundColor Yellow
    exit 1
}

Write-Host "🔧 Whitelisting tools with Windows Defender..." -ForegroundColor Cyan

foreach ($exe in $tools) {
    if (Test-Path $exe) {
        try {
            Add-MpPreference -ControlledFolderAccessAllowedApplications $exe
            Write-Host "  ✅ $([System.IO.Path]::GetFileName($exe))" -ForegroundColor Green
        } catch {
            Write-Host "  ❌ Failed: $([System.IO.Path]::GetFileName($exe)) — $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  ⚠️  Not found: $exe" -ForegroundColor Yellow
    }
}

Write-Host "`n✅ Done! The permission error should be gone now." -ForegroundColor Green
Write-Host "   Press any key to close..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
