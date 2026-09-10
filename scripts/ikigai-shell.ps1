# ikigai-shell.ps1 — Activate IKIGAI v2 harness in PowerShell (silent).
#
# UX 2026-09-10: by default runs SILENTLY (no banner spam in every new
# terminal). Pass --verbose to see the activation banner.
#
# What it does (always, silent):
#   - PREPENDs worktree .venv\Scripts to PATH (ikigai-chat on PATH)
#   - Sets PYTHONPATH to worktree root + src (so sys_ikigai imports work)
#   - Sets ANTHROPIC_BASE_URL to MiniMax proxy
#   - Leaves ANTHROPIC_API_KEY alone (you set it once; we don't echo)
#   - Falls back to IKIGAI_FAKE_LLM=1 if no API key (so ikigai-chat works
#     without burning API spend)
#
# Usage:
#   . .\scripts\ikigai-shell.ps1             # silent — just sets env
#   . .\scripts\ikigai-shell.ps1 --verbose   # prints activation banner
#   . .\scripts\ikigai-shell.ps1 --install   # writes dot-source to $PROFILE
#                                              (one-shot setup for new shells)

$ErrorActionPreference = 'Stop'

# Resolve paths relative to this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$WorktreeRoot = Split-Path -Parent $ScriptDir  # parent of scripts/

# 1. PATH — PREPEND .venv\Scripts so ikigai-chat wins PATH precedence
$VenvScripts = Join-Path $WorktreeRoot '.venv\Scripts'
if (-not (Test-Path $VenvScripts)) {
    Write-Error "venv not found at $VenvScripts. Run 'uv sync' first."
}
if ($env:PATH -notlike "*$VenvScripts*") {
    $pathsWithoutVenv = $env:PATH -split ';' | Where-Object { $_ -ne $VenvScripts }
    $env:PATH = @($VenvScripts) + $pathsWithoutVenv -join ';'
    if ($Verbose) { Write-Host "[ikigai-shell] PATH prepended with $VenvScripts" -ForegroundColor Green }
}

# 2. PYTHONPATH — ensures sys_ikigai + dotted-prefix imports resolve
$LifeSrc = Join-Path $WorktreeRoot 'src'
$IkigaiSrc = Join-Path $WorktreeRoot 'src/ikigai/src'
$Pypath = "$WorktreeRoot;$LifeSrc;$IkigaiSrc"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$Pypath;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $Pypath
}

# 3. ANTHROPIC_BASE_URL — defaults to MiniMax proxy
if (-not $env:ANTHROPIC_BASE_URL) {
    $env:ANTHROPIC_BASE_URL = 'https://api.minimax.io/anthropic'
}

# 4. ANTHROPIC_API_KEY — DO NOT set here. If unset, fall back to FAKE_LLM
if (-not $env:ANTHROPIC_API_KEY) {
    $env:IKIGAI_FAKE_LLM = '1'
}

# 5. ANTHROPIC_SMALL_FAST_MODEL — MiniMax proxy fast classifier
if (-not $env:ANTHROPIC_SMALL_FAST_MODEL) {
    $env:ANTHROPIC_SMALL_FAST_MODEL = 'MiniMax-M2.5-highspeed'
}

# --install: writes the wrapper path into $PROFILE (one-shot setup)
if ($args -contains '--install') {
    $wrapperPath = $MyInvocation.MyCommand.Definition
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
        Write-Host "[ikigai-shell] --install: already configured in profile" -ForegroundColor Yellow
        Write-Host "  $profilePath" -ForegroundColor Yellow
    } else {
        Add-Content -Path $profilePath -Value ""
        Add-Content -Path $profilePath -Value $marker
        Add-Content -Path $profilePath -Value ". `"$wrapperPath`""
        Write-Host "[ikigai-shell] --install: added to profile" -ForegroundColor Green
        Write-Host "  $profilePath" -ForegroundColor Green
    }
    return
}

# Verbose mode: print banner only if explicitly requested
if ($Verbose -or ($args -contains '--verbose')) {
    Write-Host ""
    Write-Host "[ikigai-shell] IKIGAI v2 harness activated from:" -ForegroundColor Cyan
    Write-Host "  $WorktreeRoot" -ForegroundColor White
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host "  ikigai-chat --no-chat         → print help + exit" -ForegroundColor White
    Write-Host "  ikigai-chat --prompt '...'    → one-shot agent invocation" -ForegroundColor White
    Write-Host "  ikigai-taskdog-mcp            → taskdog MCP subprocess" -ForegroundColor White
    Write-Host "  ikigai-deep-agent             → alias for ikigai-chat" -ForegroundColor White
    Write-Host "  python -m interfaces.cli v2 chat --prompt '...'" -ForegroundColor White
    Write-Host ""
}
