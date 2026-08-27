# seed_test_repo.ps1 — Windows wrapper for seed_test_repo.sh
# (Calls the bash version via Git Bash if available; otherwise minimal shim.)
param(
    [string]$Dest = "$env:TEMP\medic-demo"
)
$bash = (Get-Command bash -ErrorAction SilentlyContinue)
if ($bash) {
    & $bash "$PSScriptRoot\seed_test_repo.sh" $Dest
    return
}

# Minimal PowerShell fallback (creates the repo without bash)
Remove-Item -Recurse -Force $Dest -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "$Dest\src","$Dest\tests\golden\frames" -Force | Out-Null
Push-Location $Dest
git init -q -b main
git config user.email "medic@example.com"
git config user.name  "medic demo"

@'
[project]
name = "medic-demo"
version = "0.1.0"
'@ | Out-File -Encoding utf8 pyproject.toml

@'
# TODO: write tests
# FIXME: this is a hack
import os
PATH = "/usr/local/bin"

def add(a, b):
    return a + b
'@ | Out-File -Encoding utf8 src\calc.py

@'
from src.calc import add
def test_add():
    assert add(1, 2) == 3
'@ | Out-File -Encoding utf8 tests\test_calc.py

git add -A
git commit -q -m "feat: initial calculator"
Pop-Location
Write-Host "demo repo at $Dest"
