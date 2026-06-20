param(
    [string]$RepoPath = ".",
    [string]$SinceDate = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd"),
    [string]$UntilDate = (Get-Date).ToString("yyyy-MM-dd")
)

# Move to the specified repository
Push-Location $RepoPath
try {
    # Check if it's a git repository
    if (-not (Test-Path ".git")) {
        Write-Error "The path $RepoPath is not a git repository."
        exit 1
    }

    # Fetch git logs between SinceDate and UntilDate
    # We want commit hash, author date, and full message
    $gitFormat = "%H|%ad|%B"
    # Note: %B in git log formats can be multi-line. We'll use a separator to make parsing easier.
    # Alternatively, we can just grab subject and body. Let's use %s (subject) and %b (body).
    $gitFormat = "%H|%aI|%s %b"
    
    # We use a custom delimiter `~|~` to split records, as standard newline can be within commit bodies
    $logOutput = git log --all --since="$SinceDate 00:00:00" --until="$UntilDate 23:59:59" --format="%H|%aI|%s %b~|~"
    
    if (-not $logOutput) {
        # Return empty JSON array if no commits found
        Write-Output "[]"
        exit 0
    }

    $rawCommits = $logOutput -split "~|~" | Where-Object { $_.Trim() -ne "" }
    $results = @()

    foreach ($rawCommit in $rawCommits) {
        $parts = $rawCommit.Trim() -split '\|', 3
        if ($parts.Length -lt 3) { continue }
        
        $hash = $parts[0].Trim()
        $date = $parts[1].Trim()
        $message = $parts[2].Trim()
        
        # Regex to find mental model tags: e.g., [MM: Cybernetics] or #mental-model:Cybernetics
        # Let's support both #mental-model:xyz and [MM:xyz]
        
        $models = @()
        
        # Match #mental-model:xyz
        $matches = [regex]::Matches($message, '(?i)#mental-model:([a-z0-9_-]+)')
        foreach ($match in $matches) {
            $models += $match.Groups[1].Value.Trim()
        }
        
        # Match [MM: xyz]
        $matches2 = [regex]::Matches($message, '(?i)\[MM:\s*([^\]]+)\]')
        foreach ($match in $matches2) {
            $models += $match.Groups[1].Value.Trim()
        }
        
        # We only care about commits that have mental models applied (or maybe we want all to measure general execution)
        # But for telemetry on consolidation, we explicitly want the applied models.
        if ($models.Count -gt 0) {
            # Let's get remote URL to form a github link if possible
            $remoteUrl = git config --get remote.origin.url
            $commitLink = $hash # fallback
            
            if ($remoteUrl -match 'github\.com[:/](.+?)\.git$') {
                $repoName = $matches[1]
                $commitLink = "https://github.com/$repoName/commit/$hash"
            }
            
            $results += [PSCustomObject]@{
                CommitHash = $hash
                Date = $date
                Message = ($message -split "`n")[0] # Just the subject
                ModelsApplied = $models
                Link = $commitLink
            }
        }
    }
    
    $results | ConvertTo-Json -Depth 5 -Compress

} finally {
    Pop-Location
}
