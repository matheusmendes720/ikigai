# Taskwarrior aliases/functions for PowerShell (calls WSL task)

function wt {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    wsl -e task @Args
}

function ta { wt @args }
function tl { wt list @args }
function tn { wt next @args }
function td { wt done @args }
function tc { wt done @args }
function tld { wt 'due:today' list }
function tldt { wt 'due:tomorrow' list }
function tlh { wt 'priority:H' list }
function tlo { wt '+OVERDUE' list }
function tlp { wt projects }
function tlt { wt tags }
function ts { wt summary }
function tst { wt stats }
function tex { wt export @args }
function tim { wt import @args }
# Custom help system
# UTF-8 encoding enforcement for cross-platform compatibility
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:LESSCHARSET = "utf-8"

# Enable ANSI color support (Windows Terminal supports ANSI by default)
# For PowerShell 7+, ensure ANSI rendering is enabled
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSStyle.OutputRendering = 'Ansi'
}

$HelpScriptPath = "$PSScriptRoot\..\help\main-help.ps1"
if (Test-Path $HelpScriptPath) {
    . $HelpScriptPath
}

# Remove existing thelp/thq/th functions if they exist (to avoid parameter conflicts)
if (Get-Command thelp -ErrorAction SilentlyContinue) {
    Remove-Item Function:thelp -Force -ErrorAction SilentlyContinue
}
if (Get-Command thq -ErrorAction SilentlyContinue) {
    Remove-Item Function:thq -Force -ErrorAction SilentlyContinue
}
if (Get-Command th -ErrorAction SilentlyContinue) {
    Remove-Item Function:th -Force -ErrorAction SilentlyContinue
}

# Custom help system - th is the primary command for comprehensive help (docs 00-12)
function th {
    param(
        [Parameter(Position=0)][string]$Topic = "overview"
    )
    
    # Debug mode via environment variable
    if ($env:TASK_HELP_DEBUG -eq "1") {
        Write-Host "=== Help System Debug Info ===" -ForegroundColor Cyan
        Write-Host "OS: $($PSVersionTable.OS)" -ForegroundColor Yellow
        Write-Host "Shell: PowerShell $($PSVersionTable.PSVersion)" -ForegroundColor Yellow
        Write-Host "Encoding: $([Console]::OutputEncoding.EncodingName)" -ForegroundColor Yellow
        Write-Host "Is TTY: $([Console]::IsOutputRedirected -eq $false)" -ForegroundColor Yellow
        Write-Host "Topic: $Topic" -ForegroundColor Yellow
        Write-Host ""
    }
    
    if (Get-Command Show-TaskHelp -ErrorAction SilentlyContinue) {
        
        # Show-TaskHelp outputs directly to preserve ANSI colors
        # Capture output only if we need to page it
        if (-not [Console]::IsOutputRedirected) {
            # For TTY, capture output and split by H2 sections
            $output = Show-TaskHelp -Topic $Topic 6>&1
            $outputStr = if ($output -is [array]) { $output -join "`n" } else { $output.ToString() }
            
            # Split by H2 section breaks (inserted by format-markdown.py)
            $sections = $outputStr -split '__H2_SECTION_BREAK__'
            
            # Display content with pagination using less via WSL
            # less supports arrow keys, mouse scrolling, and better navigation
            # Combine all sections (no separators/prompts - clean output)
            $fullContent = ""
            for ($i = 0; $i -lt $sections.Count; $i++) {
                $section = $sections[$i].Trim()
                if ($section) {
                    if ($i -gt 0) {
                        $fullContent += "`n`n"
                    }
                    $fullContent += $section
                }
            }
            
            # Write to temp file and use less via WSL for full-featured pagination
            $tempFile = [System.IO.Path]::GetTempFileName()
            try {
                [System.IO.File]::WriteAllText($tempFile, $fullContent, [System.Text.Encoding]::UTF8)
                $wslTempFile = '/mnt/' + $tempFile.Substring(0,1).ToLower() + $tempFile.Substring(2).Replace('\', '/')
                
                # Use less with -R (colors), -X (no clear on exit), and ensure TTY
                # less supports arrow keys, mouse, and all navigation features
                # Don't redirect stderr to stdout - let less handle it properly to avoid file paths appearing
                wsl -e bash -c "export LC_ALL=C.UTF-8; export LANG=C.UTF-8; if [ -t 1 ]; then less -R -X '$wslTempFile'; else cat '$wslTempFile'; fi"
                
                # After user exits less (Q), print full content for reference
                Write-Host $fullContent
            } finally {
                if (Test-Path $tempFile) {
                    Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
                }
            }
        } else {
            # For piped output, just pass through (no section breaks)
            $output = Show-TaskHelp -Topic $Topic 6>&1
            $outputStr = if ($output -is [array]) { $output -join "`n" } else { $output.ToString() }
            # Remove section breaks for piped output
            $outputStr -replace '__H2_SECTION_BREAK__', '' | Write-Output
        }
    } else {
        # Fallback to WSL script (path derived from this script's location)
        $mainHelpSh = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\help\main-help.sh') -ErrorAction SilentlyContinue
        if ($mainHelpSh) {
            $winPath = $mainHelpSh.Path
            $wslPath = '/mnt/' + $winPath.Substring(0,1).ToLower() + $winPath.Substring(2).Replace('\', '/')
            $result = wsl -e bash -c "export LC_ALL=C.UTF-8; export LANG=C.UTF-8; '$wslPath' '$Topic'" 2>&1
        } else {
            $result = wsl -e task help $Topic 2>&1
        }
        if (-not [Console]::IsOutputRedirected) {
            $result | Out-Host -Paging
        } else {
            $result
        }
    }
    
    # Always return exit code 0 for help
    $LASTEXITCODE = 0
}

# Quick reference help (tabular format)
function thq {
    param(
        [Parameter(Position=0)][string]$Topic = "overview"
    )
    
    # Debug mode via environment variable
    if ($env:TASK_HELP_DEBUG -eq "1") {
        Write-Host "=== Quick Help Debug Info ===" -ForegroundColor Cyan
        Write-Host "OS: $($PSVersionTable.OS)" -ForegroundColor Yellow
        Write-Host "Encoding: $([Console]::OutputEncoding.EncodingName)" -ForegroundColor Yellow
        Write-Host "Topic: $Topic" -ForegroundColor Yellow
        Write-Host ""
    }
    
    if (Get-Command Show-TaskHelp -ErrorAction SilentlyContinue) {
        $output = Show-TaskHelp -Topic $Topic -Quick
        # Quick reference is usually short, no pagination needed
        $output
    } else {
        # Fallback to WSL script with --quick flag
        $mainHelpSh = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\help\main-help.sh') -ErrorAction SilentlyContinue
        if ($mainHelpSh) {
            $winPath = $mainHelpSh.Path
            $wslPath = '/mnt/' + $winPath.Substring(0,1).ToLower() + $winPath.Substring(2).Replace('\', '/')
            wsl -e bash -c "export LC_ALL=C.UTF-8; export LANG=C.UTF-8; '$wslPath' --quick '$Topic'"
        } else {
            wsl -e task help $Topic
        }
    }
    
    # Always return exit code 0 for help
    $LASTEXITCODE = 0
}

# Vanilla Taskwarrior help - thelp now accesses vanilla Taskwarrior help from WSL
function thelp {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    wsl -e task help @Args
    $LASTEXITCODE = $?
}

# Vanilla Taskwarrior commands list
function tcmd {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    wsl -e task commands @Args
    $LASTEXITCODE = $?
}

# Man pages - flexible version (e.g., tman task, tman taskrc)
function tman {
    param([Parameter(Position=0, Mandatory=$true)][string]$Page)
    wsl -e man "task-$Page" 2>&1
    $LASTEXITCODE = $?
}

# Man pages - individual aliases (tdoc* = task doc / man page; avoids unapproved-verb lint)
function tdoctask {
    wsl -e man task 2>&1
    $LASTEXITCODE = $?
}

function tdoctaskrc {
    wsl -e man taskrc 2>&1
    $LASTEXITCODE = $?
}

function tdoctaskcolor {
    wsl -e man task-color 2>&1
    $LASTEXITCODE = $?
}

function tdoctasksync {
    wsl -e man task-sync 2>&1
    $LASTEXITCODE = $?
}
function tall { wt all @args }
function tcomp { wt completed @args }
function tready { wt ready @args }
function tblocked { wt blocked @args }
function tactive { wt '+ACTIVE' list }
function tw { wt waiting @args }
function tcal { wt calendar @args }
function tundo { wt undo @args }
function tctxw { wt context work @args }
function tctxft { wt context focus_today @args }
function tctxwk { wt context week @args }
function tctxrev { wt context review @args }
function tctxciclo { wt context ciclo @args }
function tctxonda { wt context onda @args }
function tctxtf { wt context teste_fogo @args }
function tctx0 { wt context none @args }
function trecurd { wt add recur:daily due:today+1d @args }
function trecurw { wt add recur:weekly due:eow @args }
function trecur15 { wt add recur:2w due:today+15d @args }
function trecurm { wt add recur:monthly due:eom @args }
function twd {
    param(
        [Parameter(Mandatory = $true, Position = 0)][string]$Start,
        [Parameter(Mandatory = $true, Position = 1)][string]$Days,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
    )
    $workingDaysPy = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\scripts\working-days.py') -ErrorAction SilentlyContinue
    if ($workingDaysPy) {
        $winPath = $workingDaysPy.Path
        $wslPath = '/mnt/' + $winPath.Substring(0,1).ToLower() + $winPath.Substring(2).Replace('\', '/')
        $due = wsl -e python3 $wslPath $Start $Days
    } else {
        $due = $Start
    }
    wt add "due:$due" @Rest
}

function tm {
    Write-Host "-- Rotina Inicial (manhã) --"
    wt narrativa
    wt 'due:today' list
    wt blocos
}

function te {
    Write-Host "-- Rotina Final (noite) --"
    wt 'completed' 'end:today'
    wt 'due:tomorrow' list
}

function twk {
    Write-Host "-- Revisão Semanal --"
    wt relatorios
    wt 'modified.after:today-7d' summary
}

function tstandup {
    Write-Host "-- Standup Diário --"
    wt '+narrativa' 'due:today' list
}

function ti {
    wt @args info
}

function tstart {
    wt @args start
}

function tstop {
    wt @args stop
}

# Hierarchy shortcuts
function tsonho { wt sonho @args }
function tobj { wt objetivo @args }
function tmeta { wt meta @args }
function tmicro { wt tarefa @args }
function tbloco { wt blocos @args }

function tdiag { wt diag }

# Usage: . .\\scripts\\task-aliases.ps1
