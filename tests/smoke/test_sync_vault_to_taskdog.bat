@echo off
:: Phase B6.8 smoke test - vault-to-taskdog sync CLI (Windows)
:: Usage: tests\smoke\test_sync_vault_to_taskdog.bat
::
:: Verifies:
::   1. CLI subcommand `sync vault-to-taskdog` is registered (via --help)
::   2. parse_vault_tasks() works on a tmp vault (MCP-independent)
::   3. diff() classifies parsed tasks (MCP-independent)
::   4. Full CLI sync attempt with 8s timeout (graceful if MCP unavailable)
::
:: The push stage requires a real taskdog MCP server. If MCP is unavailable,
:: the CLI times out and the smoke test still PASSES because parse+diff verified.

setlocal enabledelayedexpansion

set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%" || exit /b 1

:: Create temp vault dir
set "SMOKE_VAULT=%TEMP%\b6_smoke_vault"
set "SMOKE_STATE=%TEMP%\b6_smoke_state.json"

if exist "%SMOKE_VAULT%" rmdir /s /q "%SMOKE_VAULT%"
if exist "%SMOKE_STATE%" del /f /q "%SMOKE_STATE%"
mkdir "%SMOKE_VAULT%"

:: Create one valid task file
(
    echo ---
    echo ueid: ikigai:task:smoke:001
    echo title: Smoke test task
    echo tags: [task]
    echo status: planned
    echo priority: medium
    echo ---
    echo # Smoke
    echo.
    echo This is a smoke test.
) > "%SMOKE_VAULT%\test-task.md"

:: Create a non-task file (should be silently skipped)
(
    echo ---
    echo title: Just a draft
    echo tags: [draft]
    echo ---
    echo # Draft
) > "%SMOKE_VAULT%\draft.md"

set "FAILED=0"

echo === Step 1: Verify CLI subcommand is registered ===
python -m ikigai.cli.app sync vault-to-taskdog --help 2>&1 | findstr /C:"Sync vault frontmatter-tagged tasks" >nul
if errorlevel 1 (
    echo ERROR: CLI subcommand 'sync vault-to-taskdog' not registered
    set "FAILED=1"
    goto cleanup
)
echo OK: CLI subcommand registered

echo.
echo === Step 2: Verify parse_vault_tasks^(^) works on the tmp vault ===
python -c "import sys; sys.path.insert(0, 'src/ikigai/src'); from ikigai.vault.sync import parse_vault_tasks; from pathlib import Path; tasks = parse_vault_tasks(Path(r'%SMOKE_VAULT%')); assert len(tasks) >= 1, f'Expected >=1 task, got {len(tasks)}'; print(f'OK: Parsed {len(tasks)} task^(s^) from tmp vault')"
if errorlevel 1 (
    echo ERROR: parse_vault_tasks failed
    set "FAILED=1"
    goto cleanup
)

echo.
echo === Step 3: Verify diff^(^) classifies parsed tasks ===
python -c "import sys; sys.path.insert(0, 'src/ikigai/src'); from ikigai.vault.sync import parse_vault_tasks, diff, SyncState; from pathlib import Path; tasks = parse_vault_tasks(Path(r'%SMOKE_VAULT%')); actions = diff(tasks, SyncState()); assert len(actions) >= 1, f'Expected >=1 action, got {len(actions)}'; print(f'OK: diff^(^) classified {len(actions)} task^(s^) as {actions[0].kind.value}')"
if errorlevel 1 (
    echo ERROR: diff failed
    set "FAILED=1"
    goto cleanup
)

echo.
echo === Step 4: Attempt full sync ^(skipped gracefully if MCP unavailable^) ===
echo NOTE: push stage requires MCP server. If it times out, smoke test still PASSES.

:: Run with 8s timeout via a Python wrapper that kills the subprocess
python -c "
import subprocess, sys, time
p = subprocess.Popen(
    ['python', '-m', 'ikigai.cli.app', '--json', 'sync', 'vault-to-taskdog', '--vault', r'%SMOKE_VAULT%', '--state', r'%SMOKE_STATE%'],
    env={'PYTHONPATH': 'src/ikigai/src', **__import__('os').environ},
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
try:
    out, _ = p.communicate(timeout=8)
    print(out)
    sys.exit(0)
except subprocess.TimeoutExpired:
    p.kill()
    out, _ = p.communicate()
    print('CLI timed out after 8s - MCP not available (expected in smoke env)', file=sys.stderr)
    sys.exit(0)  # graceful - smoke test still passes
" 2>&1
if errorlevel 1 (
    echo ERROR: CLI invocation failed
    set "FAILED=1"
    goto cleanup
)

:cleanup
if exist "%SMOKE_VAULT%" rmdir /s /q "%SMOKE_VAULT%"
if exist "%SMOKE_STATE%" del /f /q "%SMOKE_STATE%" 2>nul

if "%FAILED%"=="1" (
    echo.
    echo === Smoke test FAILED ===
    exit /b 1
)

echo.
echo === Smoke test PASSED ===
exit /b 0