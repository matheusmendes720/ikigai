@echo off
REM Windows wrapper for MCP gateway contract test.
REM Equivalent to `python scripts/mcp_inspect.py` — provided because
REM `make` is not on PATH for some Windows shells (cmd, Windows Terminal).

setlocal
set "REPO_ROOT=%~dp0.."
set "PYTHONPATH=%REPO_ROOT%;%REPO_ROOT%\src\ikigai\src"
python "%REPO_ROOT%\scripts\mcp_inspect.py" %*
endlocal
