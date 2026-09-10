# install.ps1 — one-shot setup for IKIGAI v2 harness on this machine.
#
# Run from PowerShell (admin recommended but not required):
#   .\scripts\install.ps1
#
# What it does:
#   1. Adds .venv\Scripts to Windows user PATH (persistent, survives restarts)
#   2. Adds ikigai-shell.ps1 to $PROFILE (loads PATH + env vars per session)
#   3. Removes the conflicting 'dcode' PowerShell alias (points to dcodetui)
#   4. Documents remaining manual steps
#
# Idempotent — safe to re-run.

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$WorktreeRoot = Split-Path -Parent $ScriptDir
$VenvScripts = Join-Path $WorktreeRoot '.venv\Scripts'
$Wrapper = Join-Path $ScriptDir 'ikigai-shell.ps1'

Write-Host "[install] IKIGAI v2 harness one-shot setup" -ForegroundColor Cyan
Write-Host "[install] Worktree: $WorktreeRoot" -ForegroundColor White
Write-Host ""

# 1. Add venv Scripts to Windows user PATH (persistent)
Write-Host "[1/3] Windows user PATH..." -ForegroundColor Yellow
$currentPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($currentPath -like "*$VenvScripts*") {
    Write-Host "  already in PATH: $VenvScripts" -ForegroundColor Green
} else {
    $newPath = "$currentPath;$VenvScripts"
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Write-Host "  added to user PATH: $VenvScripts" -ForegroundColor Green
    Write-Host "  (takes effect in NEW PowerShell windows)" -ForegroundColor Yellow
}
Write-Host ""

# 2. Add ikigai-shell.ps1 to $PROFILE (so wrapper runs in every session)
Write-Host "[2/3] PowerShell profile..." -ForegroundColor Yellow
$profilePath = $PROFILE
$profileDir = Split-Path -Parent $profilePath
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}
if (-not (Test-Path $profilePath)) {
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
}
$existing = Get-Content $profilePath -ErrorAction SilentlyContinue
$marker = "# ikigai-chat — IKIGAI v2 harness activation (UX 2026-09-10)"
if ($existing -and ($existing -match [regex]::Escape($marker))) {
    Write-Host "  already in \$PROFILE" -ForegroundColor Green
} else {
    Add-Content -Path $profilePath -Value ""
    Add-Content -Path $profilePath -Value $marker
    Add-Content -Path $profilePath -Value ". `"$Wrapper`""
    Write-Host "  added wrapper to profile: $profilePath" -ForegroundColor Green
}
Write-Host ""

# 3. Remove conflicting 'dcode' PowerShell alias (pointed to dcodetui).
# This is the alias that was making 'dcode' silently launch dcodetui
# instead of the ikigai-chat we expected. We don't remove the
# dcodetui function — just unregister the 'dcode' alias so users
# type 'ikigai-chat' instead.
Write-Host "[3/3] Remove conflicting 'dcode' PowerShell alias..." -ForegroundColor Yellow
$aliases = Get-Alias -Name 'dcode' -ErrorAction SilentlyContinue
if ($aliases) {
    foreach ($a in $aliases) {
        Write-Host "  found alias: $($a.Definition) (source: $($a.Source))" -ForegroundColor Yellow
    }
    Remove-Item Alias:\dcode -Force -ErrorAction SilentlyContinue
    Write-Host "  removed dcode alias (now you must use 'ikigai-chat' instead)" -ForegroundColor Green
} else {
    Write-Host "  no dcode alias found — nothing to remove" -ForegroundColor Green
}
Write-Host ""

Write-Host "[install] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. CLOSE this PowerShell window" -ForegroundColor White
Write-Host "  2. OPEN a NEW PowerShell window (so PATH and \$PROFILE reload)" -ForegroundColor White
Write-Host "  3. Type 'ikigai-chat --no-chat' — should work without any setup" -ForegroundColor White
Write-Host ""
Write-Host "If ikigai-chat is still not recognized:" -ForegroundColor Yellow
Write-Host "  - Check: [Environment]::GetEnvironmentVariable('Path', 'User')" -ForegroundColor White
Write-Host "  - Should contain: $VenvScripts" -ForegroundColor White
Write-Host ""
