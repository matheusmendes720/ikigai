@echo off
REM Phase B6 Task 4 smoke test — vault-from-taskdog CLI (Windows)
REM Usage: tests\smoke\test_reverse_sync_vault_from_taskdog.bat
setlocal

cd /d "%~dp0\..\.."

echo === Step 1: Verify CLI subcommand is registered ===
set PYTHONPATH=src\ikigai\src
python -c "from ikigai.cli.app import sync_vault_from_taskdog; print('sync_vault_from_taskdog callable exists')"
if errorlevel 1 (
    echo ERROR: CLI subcommand not registered
    exit /b 1
)
echo = Step 1 PASSED

echo === Step 2: Verify reverse_sync module exists ===
set PYTHONPATH=src\ikigai\src
python -c "from ikigai.vault.sync import reverse_sync; print('reverse_sync exists')"
if errorlevel 1 (
    echo ERROR: reverse_sync module not found
    exit /b 1
)
echo = Step 2 PASSED

echo === Step 3: Verify CLI --dry-run flag ===
set PYTHONPATH=src\ikigai\src
python -c "from ikigai.cli.app import sync_vault_from_taskdog; import inspect; sig = inspect.signature(sync_vault_from_taskdog); assert 'dry_run' in sig.parameters; print('dry_run flag present')"
if errorlevel 1 (
    echo ERROR: dry_run flag not present
    exit /b 1
)
echo = Step 3 PASSED

echo === Step 4: Verify CLI --help works ===
set PYTHONPATH=src\ikigai\src
python -m ikigai.cli.app sync vault-from-taskdog --help > nul
if errorlevel 1 (
    echo ERROR: CLI help failed
    exit /b 1
)
echo = Step 4 PASSED

echo === Smoke test PASSED ===
