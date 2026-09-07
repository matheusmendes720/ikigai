# Loop Engineering — life-oss install / verification
# Run this once after the loop files are created.
# Verifies everything is in place and (optionally) wires to the claude-flow daemon.

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot | Split-Path -Parent | Split-Path -Parent
$loopDir = Join-Path $projectRoot '.claude\loop'

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Loop Engineering — life-oss install" -ForegroundColor Cyan
Write-Host "  Project root: $projectRoot" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check required files
Write-Host "[1/5] Checking required files..." -ForegroundColor Yellow
$required = @(
    "$loopDir\roadmap.md",
    "$loopDir\tasks.md",
    "$loopDir\progress.md",
    "$loopDir\constitution.md",
    "$loopDir\loop-tick.sh",
    "$loopDir\loop-tick.bat",
    "$loopDir\hill-climb.sh",
    "$loopDir\CURATED-TECHNIQUES.md",
    "$loopDir\README.md",
    "$projectRoot\.claude\skills\loop-engineering\SKILL.md",
    "$projectRoot\.claude\agents\loop\orchestrator.md",
    "$projectRoot\.claude\agents\loop\worker.md",
    "$projectRoot\.claude\agents\loop\verifier.md",
    "$projectRoot\scripts\worktree-helper.sh"
)
$allOk = $true
foreach ($f in $required) {
    if (Test-Path $f) {
        $size = (Get-Item $f).Length
        Write-Host "  ✓ $($f.Substring($projectRoot.Length + 1)) ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MISSING: $($f.Substring($projectRoot.Length + 1))" -ForegroundColor Red
        $allOk = $false
    }
}
if (-not $allOk) {
    Write-Host ""
    Write-Host "Some files are missing. Please check the loop/ directory." -ForegroundColor Red
    exit 1
}

# Check claude-flow daemon manager
Write-Host ""
Write-Host "[2/5] Checking claude-flow integration..." -ForegroundColor Yellow
$daemonScript = Join-Path $projectRoot '.claude\helpers\daemon-manager.sh'
if (Test-Path $daemonScript) {
    Write-Host "  ✓ daemon-manager.sh exists" -ForegroundColor Green
    Write-Host "    To register the loop-tick, run:" -ForegroundColor Gray
    Write-Host "    bash $daemonScript add --name loop-tick --interval 60m --command 'bash $loopDir\loop-tick.sh' --cost-cap-usd 5" -ForegroundColor Gray
} else {
    Write-Host "  ✗ daemon-manager.sh not found" -ForegroundColor Red
}

# Check IKIGAi MCP
Write-Host ""
Write-Host "[3/5] Checking IKIGAi MCP..." -ForegroundColor Yellow
$mcpJson = Join-Path $projectRoot '.mcp.json'
if (Test-Path $mcpJson) {
    $mcp = Get-Content $mcpJson -Raw | ConvertFrom-Json
    if ($mcp.mcpServers.ikigai) {
        Write-Host "  ✓ IKIGAi MCP server registered" -ForegroundColor Green
    } else {
        Write-Host "  ! IKIGAi MCP not found in .mcp.json" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ .mcp.json not found" -ForegroundColor Red
}

# Check LangGraph graphs
Write-Host ""
Write-Host "[4/5] Checking LangGraph graphs..." -ForegroundColor Yellow
$langgraphJson = Join-Path $projectRoot 'langgraph.json'
if (Test-Path $langgraphJson) {
    $lg = Get-Content $langgraphJson -Raw | ConvertFrom-Json
    Write-Host "  ✓ $($lg.graphs.PSObject.Properties.Count) LangGraph graphs registered:" -ForegroundColor Green
    foreach ($g in $lg.graphs.PSObject.Properties) {
        Write-Host "    - $($g.Name): $($g.Value)" -ForegroundColor Gray
    }
}

# Final summary
Write-Host ""
Write-Host "[5/5] Summary" -ForegroundColor Yellow
Write-Host "  Loop engineering pattern: READY" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Dry run:" -ForegroundColor White
Write-Host "     bash $loopDir\loop-tick.sh --dry-run" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. First manual tick:" -ForegroundColor White
Write-Host "     bash $loopDir\loop-tick.sh" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Check progress:" -ForegroundColor White
Write-Host "     cat $loopDir\progress.md" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. After 3-5 successful manual ticks, schedule via daemon:" -ForegroundColor White
Write-Host "     bash $projectRoot\.claude\helpers\daemon-manager.sh add ``" -ForegroundColor Gray
Write-Host "       --name loop-tick ``" -ForegroundColor Gray
Write-Host "       --interval 60m ``" -ForegroundColor Gray
Write-Host "       --command 'bash $loopDir\loop-tick.sh' ``" -ForegroundColor Gray
Write-Host "       --cost-cap-usd 5" -ForegroundColor Gray
Write-Host ""
Write-Host "  5. Weekly hill-climb (after M3):" -ForegroundColor White
Write-Host "     bash $loopDir\hill-climb.sh" -ForegroundColor Gray
Write-Host ""
Write-Host "Done." -ForegroundColor Green
