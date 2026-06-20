# Markdown formatter with colors for PowerShell
# Formats markdown files with colors for better readability

function Format-Markdown {
    param([string]$FilePath)
    
    if (-not (Test-Path $FilePath)) {
        Write-Host "File not found: $FilePath" -ForegroundColor Red
        return
    }
    
    $lines = Get-Content $FilePath
    $inCodeBlock = $false
    
    foreach ($line in $lines) {
        # Code blocks
        if ($line -match '^```') {
            $inCodeBlock = -not $inCodeBlock
            Write-Host $line -ForegroundColor DarkGray
            continue
        }
        
        if ($inCodeBlock) {
            # Inside code block
            Write-Host $line -ForegroundColor Cyan
            continue
        }
        
        # Headers
        if ($line -match '^#+\s+') {
            $level = ($line | Select-String -Pattern '^(#+)').Matches[0].Groups[1].Value.Length
            
            switch ($level) {
                1 { Write-Host $line -ForegroundColor Cyan }
                2 { Write-Host $line -ForegroundColor Yellow }
                3 { Write-Host $line -ForegroundColor Green }
                4 { Write-Host $line -ForegroundColor Magenta }
                default { Write-Host $line -ForegroundColor Green }
            }
            continue
        }
        
        # Horizontal rules
        if ($line -match '^---') {
            Write-Host "────────────────────────────────────────────────────────" -ForegroundColor Gray
            continue
        }
        
        # Process line with formatting
        $formatted = $line
        
        # Protect inline code first
        $codePlaceholders = @{}
        $codeIdx = 0
        $formatted = [regex]::Replace($formatted, '`([^`]+)`', {
            param($match)
            $placeholder = "__CODE_$codeIdx__"
            $codePlaceholders[$placeholder] = $match.Groups[1].Value
            $script:codeIdx++
            return $placeholder
        })
        
        # Bold text (**text**)
        $formatted = [regex]::Replace($formatted, '\*\*([^*]+)\*\*', {
            param($match)
            Write-Host $match.Groups[1].Value -NoNewline -ForegroundColor White
            return $match.Groups[1].Value
        })
        # Better: use escape sequences
        $formatted = $formatted -replace '\*\*([^*]+)\*\*', "$([char]27)[1;37m`$1$([char]27)[0m"
        
        # Restore inline code
        foreach ($placeholder in $codePlaceholders.Keys) {
            $codeContent = $codePlaceholders[$placeholder]
            $formatted = $formatted -replace [regex]::Escape($placeholder), "$([char]27)[0;36m$codeContent$([char]27)[0m"
        }
        
        # Aliases/Commands
        $aliases = @('thelp', 'th', 'ta', 'tl', 'tn', 'td', 'tc', 'tm', 'te', 'twk', 
                     'tsonho', 'tobj', 'tmeta', 'tmicro', 'tbloco', 
                     'tctxw', 'tctxft', 'tctxwk', 'tctxrev', 'tctxciclo', 'tctxonda', 'tctxtf', 'tctx0',
                     'trecurd', 'trecurw', 'trecur15', 'trecurm', 'twd', 'task', 'wt')
        foreach ($alias in $aliases) {
            $pattern = "\b($alias)\b"
            $formatted = $formatted -replace $pattern, "$([char]27)[1;93m`$1$([char]27)[0m"
        }
        
        # Bullet points
        if ($formatted -match '^-') {
            $formatted = $formatted -replace '^-', "$([char]27)[0;33m•$([char]27)[0m "
        }
        
        # Output formatted line using Write-Host with raw ANSI codes
        [Console]::WriteLine($formatted)
    }
}
