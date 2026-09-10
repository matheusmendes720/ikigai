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

# 1. PATH — adds .venv\Scripts so dcode.exe + ikigai.bat are callable
$VenvScripts = Join-Path $WorktreeRoot '.venv\Scripts'
if (-not (Test-Path $VenvScripts)) {
    Write-Error "venv not found at $VenvScripts. Run 'uv sync' first."
}
if ($env:PATH -notlike "*$VenvScripts*") {
    $env:PATH = "$VenvScripts;$env:PATH"
    Write-Host "[ikigai-shell] PATH += $VenvScripts" -ForegroundColor Green
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
Write-Host "Available commands:" -ForegroundColor Cyan
Write-Host "  dcode                  → chat REPL (real LLM if ANTHROPIC_API_KEY set)" -ForegroundColor White
Write-Host "  dcode --no-chat        → print help + exit" -ForegroundColor White
Write-Host "  dcode --prompt '...'   → one-shot agent invocation" -ForegroundColor White
Write-Host "  ikigai-taskdog-mcp     → taskdog MCP subprocess (Path 3)" -ForegroundColor White
Write-Host "  ikigai-deep-agent      → alias for dcode" -ForegroundColor White
Write-Host "  python -m interfaces.cli v2 chat --prompt '...'" -ForegroundColor White
Write-Host "  python -m interfaces.tui.operator.main   → TUI operator" -ForegroundColor White
Write-Host ""
Write-Host "Quick test (no LLM):" -ForegroundColor Cyan
Write-Host "  dcode --no-chat" -ForegroundColor White
Write-Host ""
