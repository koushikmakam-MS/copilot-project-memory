<#
.SYNOPSIS
  Whitelist copilot-memory tools with Windows Defender Controlled Folder Access.
  MUST be run as Administrator (right-click PowerShell → Run as administrator).
#>

$ErrorActionPreference = "Stop"

$tools = @(
    "C:\Users\koushikmakam\AppData\Local\Programs\Python\Python311\Scripts\aipipeline.exe",
    "C:\Users\koushikmakam\AppData\Local\Programs\Python\Python311\Scripts\copilot-memory.exe",
    "C:\Users\koushikmakam\AppData\Local\Programs\Python\Python311\python.exe"
)

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
