# Custom Taskwarrior Help System Router (PowerShell)
# Routes to different help topics based on argument

function Show-TaskHelp {
    param(
        [Parameter(Position=0)]
        [string]$Topic = "overview",
        [switch]$Quick
    )

    $HelpDir = Join-Path $PSScriptRoot "content"

    # Map topic names to files
    $FileMap = @{
        "overview" = "00-overview.md"
        "00" = "00-overview.md"
        "" = "00-overview.md"
        "hierarchy" = "01-hierarchy.md"
        "01" = "01-hierarchy.md"
        "hier" = "01-hierarchy.md"
        "workflows" = if ($Quick) { "workflows-quick.md" } else { "02-workflows.md" }
        "02" = if ($Quick) { "workflows-quick.md" } else { "02-workflows.md" }
        "workflow" = if ($Quick) { "workflows-quick.md" } else { "02-workflows.md" }
        "filters" = if ($Quick) { "filters-quick.md" } else { "03-filters.md" }
        "03" = if ($Quick) { "filters-quick.md" } else { "03-filters.md" }
        "filter" = if ($Quick) { "filters-quick.md" } else { "03-filters.md" }
        "args" = "04-args.md"
        "04" = "04-args.md"
        "arguments" = "04-args.md"
        "parameters" = "04-args.md"
        "flags" = "05-flags.md"
        "05" = "05-flags.md"
        "flag" = "05-flags.md"
        "modifiers" = "05-flags.md"
        "reports" = if ($Quick) { "reports-quick.md" } else { "06-reports.md" }
        "06" = if ($Quick) { "reports-quick.md" } else { "06-reports.md" }
        "report" = if ($Quick) { "reports-quick.md" } else { "06-reports.md" }
        "contexts" = "07-contexts.md"
        "07" = "07-contexts.md"
        "context" = "07-contexts.md"
        "recurrence" = "08-recurrence.md"
        "08" = "08-recurrence.md"
        "recur" = "08-recurrence.md"
        "udas" = if ($Quick) { "udas-quick.md" } else { "09-udas.md" }
        "09" = if ($Quick) { "udas-quick.md" } else { "09-udas.md" }
        "uda" = if ($Quick) { "udas-quick.md" } else { "09-udas.md" }
        "aliases" = if ($Quick) { "aliases-quick.md" } else { "10-aliases.md" }
        "10" = if ($Quick) { "aliases-quick.md" } else { "10-aliases.md" }
        "alias" = if ($Quick) { "aliases-quick.md" } else { "10-aliases.md" }
        "blocks" = "11-blocks.md"
        "11" = "11-blocks.md"
        "block" = "11-blocks.md"
        "blocos" = "11-blocks.md"
        "metrics" = "12-metrics.md"
        "12" = "12-metrics.md"
        "metric" = "12-metrics.md"
    }

    if ($FileMap.ContainsKey($Topic)) {
        $BaseFile = $FileMap[$Topic]
        $HelpFile = Join-Path $HelpDir $BaseFile
        
        if (Test-Path $HelpFile) {
            # Use Python formatter via WSL (best results)
            if ($Quick) {
                $PythonFormatter = Join-Path $PSScriptRoot "format-quick.py"
            } else {
                $PythonFormatter = Join-Path $PSScriptRoot "format-markdown.py"
            }

            if (Test-Path $PythonFormatter) {
                # Convert Windows path to WSL path (drive letter -> /mnt/x)
                $ToWslPath = { param($p) '/mnt/' + $p.Substring(0,1).ToLower() + $p.Substring(2).Replace('\', '/') }
                $WslPath = & $ToWslPath $HelpFile
                $WslFormatter = & $ToWslPath $PythonFormatter
                
                # Set UTF-8 environment in WSL and force colors (WSL->PowerShell interop)
                # Force colors because WSL doesn't detect TTY correctly when called from PowerShell
                wsl -e bash -c "export LC_ALL=C.UTF-8; export LANG=C.UTF-8; export TASK_HELP_FORCE_COLORS=1; python3 $WslFormatter $WslPath" 2>&1
                return
            } else {
                # Fallback: try PowerShell formatter
                $FormatterPath = Join-Path (Split-Path $PSScriptRoot) "format-markdown.ps1"
                if (Test-Path $FormatterPath) {
                    . $FormatterPath
                    Format-Markdown -FilePath $HelpFile
                } else {
                    # Last resort: basic formatting
                    Get-Content $HelpFile -Encoding UTF8 | ForEach-Object {
                        if ($_ -match '^#+\s+') {
                            Write-Host $_ -ForegroundColor Cyan
                        } elseif ($_ -match '^---') {
                            Write-Host "────────────────────────────────────────────────────────" -ForegroundColor Gray
                        } elseif ($_ -match '```') {
                            Write-Host $_ -ForegroundColor DarkGray
                        } else {
                            Write-Host $_
                        }
                    }
                }
            }
        } else {
            Write-Host "Help file not found: $HelpFile" -ForegroundColor Red
            Write-Host "Available topics: overview, hierarchy, workflows, filters, args, flags, reports, contexts, recurrence, udas, aliases, blocks, metrics"
        }
    } else {
        # Fallback to vanilla Taskwarrior help
        wsl -e task help $Topic
    }
}
