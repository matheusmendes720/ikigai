# M123 — setup-task-scheduler.ps1
#
# One-time setup script for Windows. Registers cron-backtest.sh as a daily
# scheduled task running at 06:00 local time.
#
# Run from PowerShell as the user who owns the repo:
#   .\scripts\cron\setup-task-scheduler.ps1
#
# To unregister:
#   .\scripts\cron\setup-task-scheduler.ps1 -Unregister

param(
    [switch]$Unregister,
    [string]$Time = "06:00",
    [string]$RepoPath = (Resolve-Path "$PSScriptRoot\..\..").Path
)

$TaskName = "life-oss-backtest-daily"
$ScriptPath = Join-Path $RepoPath "scripts\cron\cron-backtest.sh"
$Bash = (Get-Command bash -ErrorAction SilentlyContinue).Source

if (-not $Bash) {
    Write-Error "bash not found on PATH. Install Git Bash or WSL."
    exit 1
}

if ($Unregister) {
    Write-Host "Unregistering task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Done."
    exit 0
}

$Action = New-ScheduledTaskAction -Execute $Bash -Argument "`"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Idempotent: unregister first if it exists, then re-register.
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily backtest pipeline for life-oss (M123). Runs cron-backtest.sh at $Time local time. Logs to .life/logs/cron-backtest.log." `
    -ErrorAction Stop

Write-Host "Registered '$TaskName' — daily at $Time"
Write-Host "Bash: $Bash"
Write-Host "Script: $ScriptPath"
Write-Host "Logs: $RepoPath\.life\logs\cron-backtest.log"
Write-Host ""
Write-Host "To unregister:"
Write-Host "  .\scripts\cron\setup-task-scheduler.ps1 -Unregister"
