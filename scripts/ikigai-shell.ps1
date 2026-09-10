# ikigai-shell.ps1 — Activate IKIGAI v2 harness in PowerShell.
#
# One-time setup (run from worktree root):
#   . .\scripts\ikigai-shell.ps1
#
# OR add to your PowerShell profile ($PROFILE):
#   notepad $PROFILE
#   # append:
#   . "C:\Users\mathe\code_space\life-oss\life\.worktrees\loop-prod-ready\scripts\ikigai-shell.ps1"
#
# What it does:
#   - Adds worktree .venv\Scripts to PATH (dcode, ikigai.bat accessible globally)
#   - Sets PYTHONPATH to worktree root + src (so sys_ikigai imports work)
#   - Sets ANTHROPIC_BASE_URL to MiniMax proxy
#   - Leaves ANTHROPIC_API_KEY alone (you set it once; we don't echo)
#   - Optional: set IKIGAI_FAKE_LLM=1 to disable LLM calls (for testing)

$ErrorActionPreference = 'Stop'

# Resolve paths relative to this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$WorktreeRoot = Split-Path -Parent $ScriptDir  # parent of scripts/

# 1. PATH — PREPEND .venv\Scripts so dcode.exe + ikigai.bat win PATH
# precedence over Python314\Scripts (which has an unrelated dcode.exe
# shadowing our harness). UX 2026-09-10: prepend (not append) so our
# `dcode` beats the Python user install's `dcode`.
$VenvScripts = Join-Path $WorktreeRoot '.venv\Scripts'
if (-not (Test-Path $VenvScripts)) {
    Write-Error "venv not found at $VenvScripts. Run 'uv sync' first."
}
if ($env:PATH -notlike "*$VenvScripts*") {
    # Filter out existing venv Scripts path (shouldn't be there yet),
    # then prepend our path so our .exes win PATH precedence.
    $pathsWithoutVenv = $env:PATH -split ';' | Where-Object { $_ -ne $VenvScripts }
    $env:PATH = @($VenvScripts) + $pathsWithoutVenv -join ';'
    Write-Host "[ikigai-shell] PATH prepended with $VenvScripts" -ForegroundColor Green
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
Write-Host "[ikigai-shell] PYTHONPATH = $env:PYTHONPATH" -ForegroundColor Green

# 3. ANTHROPIC_BASE_URL — defaults to MiniMax proxy (no LLM spend by default)
if (-not $env:ANTHROPIC_BASE_URL) {
    $env:ANTHROPIC_BASE_URL = 'https://api.minimax.io/anthropic'
    Write-Host "[ikigai-shell] ANTHROPIC_BASE_URL = https://api.minimax.io/anthropic" -ForegroundColor Yellow
}

# 4. ANTHROPIC_API_KEY — DO NOT set here. User must export it themselves.
#    If not set, dcode.exe --chat will still work in FAKE_LLM mode.
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Host "[ikigai-shell] ANTHROPIC_API_KEY not set. dcode.exe --chat will use IKIGAI_FAKE_LLM=1 (no LLM call)." -ForegroundColor Yellow
    $env:IKIGAI_FAKE_LLM = '1'
}

# 5. ANTHROPIC_SMALL_FAST_MODEL — used by MiniMax proxy for fast classification
if (-not $env:ANTHROPIC_SMALL_FAST_MODEL) {
    $env:ANTHROPIC_SMALL_FAST_MODEL = 'MiniMax-M2.5-highspeed'
}

# 6. Worktree marker so user knows they're inside
Write-Host ""
Write-Host "[ikigai-shell] IKIGAI v2 harness activated from:" -ForegroundColor Cyan
Write-Host "  $WorktreeRoot" -ForegroundColor White
Write-Host ""
Write-Host "Available commands (UX 2026-09-10: dcode renamed to ikigai-chat to" -ForegroundColor Cyan
Write-Host "avoid collision with PowerShell alias 'dcode' -> 'dcodetui'):" -ForegroundColor Cyan
Write-Host "  ikigai-chat             → chat REPL (real LLM if ANTHROPIC_API_KEY set)" -ForegroundColor White
Write-Host "  ikigai-chat --no-chat   → print help + exit" -ForegroundColor White
Write-Host "  ikigai-chat --prompt '...' → one-shot agent invocation" -ForegroundColor White
Write-Host "  ikigai-taskdog-mcp      → taskdog MCP subprocess (Path 3)" -ForegroundColor White
Write-Host "  ikigai-deep-agent       → alias for ikigai-chat (same main())" -ForegroundColor White
Write-Host "  python -m interfaces.cli v2 chat --prompt '...'" -ForegroundColor White
Write-Host "  python -m interfaces.tui.operator.main   → TUI operator" -ForegroundColor White
Write-Host ""
Write-Host ""
Write-Host "Tip: 'dcode' inside Claude Code multiplex = Claude Code's" -ForegroundColor Red
Write-Host "deepagents runtime (NOT our harness). Use 'ikigai-chat' here too." -ForegroundColor Red
Write-Host ""
Write-Host "Quick test (no LLM):" -ForegroundColor Cyan
Write-Host "  ikigai-chat --no-chat" -ForegroundColor White
Write-Host ""

# UX 2026-09-10: --install flag writes the wrapper path into $PROFILE
# so every new PowerShell window opens with ikigai-chat available.
# Idempotent — checks if line already exists before appending.
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
        Write-Host "[ikigai-shell] --install: already configured in \$PROFILE" -ForegroundColor Yellow
        Write-Host "  $profilePath" -ForegroundColor Yellow
    } else {
        Add-Content -Path $profilePath -Value ""
        Add-Content -Path $profilePath -Value $marker
        Add-Content -Path $profilePath -Value ". `"$wrapperPath`""
        Write-Host "[ikigai-shell] --install: added to \$PROFILE" -ForegroundColor Green
        Write-Host "  $profilePath" -ForegroundColor Green
        Write-Host ""
        Write-Host "Open a NEW PowerShell window and `ikigai-chat` will work globally." -ForegroundColor Cyan
    }
    return
}
