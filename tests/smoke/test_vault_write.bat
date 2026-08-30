@echo off
REM Smoke: vault_write MCP tool wiring + safety (Windows)
REM Usage: tests\smoke\test_vault_write.bat
setlocal enabledelayedexpansion

cd /d "%~dp0\..\.."

echo === Step 1: Verify vault_write function is importable via PYTHONPATH=. ===
set PYTHONPATH=.
python -c "from src.ikigai.src.ikigai.vault.vault_write import vault_write; print('vault_write callable OK')"
if errorlevel 1 (
    echo FAIL: vault_write not importable
    exit /b 1
)

echo.
echo === Step 2: Verify @MCP.tool(name="vault_write") decorator in server.py ===
findstr /C:'@MCP.tool' src\ikigai\src\mcp_server\server.py >nul
if errorlevel 1 (
    echo FAIL: @MCP.tool decorator not found
    exit /b 1
)
findstr /C:'name="vault_write"' src\ikigai\src\mcp_server\server.py >nul
if errorlevel 1 (
    echo FAIL: name="vault_write" not found
    exit /b 1
)
echo vault_write tool wired via @MCP.tool OK

echo.
echo === Step 3: Verify path traversal rejection (absolute path raises ValueError) ===
python -c "
from pathlib import Path
from src.ikigai.src.ikigai.vault.vault_write import vault_write
try:
    vault_write(
        vault_root=Path('.'),
        vault_path='C:\Windows\System32\config\SAM.md',
        frontmatter_fields={'x': 1},
        body='bad',
    )
    print('FAIL: absolute path not blocked')
    exit(1)
except ValueError as e:
    print(f'Absolute path blocked: {e}')
"
if errorlevel 1 (
    echo FAIL: path traversal not rejected
    exit /b 1
)

echo.
echo === Step 4: Verify atomic no .tmp leftover ===
set TMPDIR=%TEMP%\vault_write_smoke_%RANDOM%
mkdir "%TMPDIR%"
python -c "
from pathlib import Path
from src.ikigai.src.ikigai.vault.vault_write import vault_write
import glob as g

vault_root = Path(r'%TMPDIR%\vault')
vault_root.mkdir(parents=True)
vault_write(
    vault_root=vault_root,
    vault_path='test.md',
    frontmatter_fields={'ueid': 'task:t:abc:def', 'title': 'Test', 'status': 'planned'},
    body='# Test',
)
tmp_files = g.glob(str(vault_root / '*.tmp'))
if tmp_files:
    print(f'FAIL: leftover .tmp files: {tmp_files}')
    exit(1)
else:
    print('No .tmp leftover OK')
"
set SPYRESULT=!errorlevel!
rmdir /s /q "%TMPDIR%"
if %SPYRESULT% neq 0 (
    echo FAIL: .tmp leftover check failed
    exit /b 1
)

echo.
echo === Smoke test PASSED ===
