@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM td-chat-setup.bat — interactive setup for the td chat dev environment
REM
REM 1. Checks .env exists, is UTF-8, has LLM key
REM 2. Verifies Python venv + packages
REM 3. Shows what to do next
REM
REM Usage:  td-chat-setup.bat
REM ============================================================================

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ============================================================
echo  Life-OSS -- td chat setup check
echo ============================================================
echo.

REM Locate Python first (used by all checks)
set "PYTHON="
if exist "%ROOT%src\ikigai\.venv\Scripts\python.exe" set "PYTHON=%ROOT%src\ikigai\.venv\Scripts\python.exe"
if "%PYTHON%"=="" (
    where python >nul 2>&1 && set "PYTHON=python"
)

set "ISSUES=0"

REM ------------------------------------------------------------------------
REM 1. .env file checks
REM ------------------------------------------------------------------------
echo [1] .env file checks:
if exist "%ROOT%.env" (
    echo    OK .env exists at %ROOT%.env
) else (
    echo    MISSING .env
    echo      Create it with: notepad .env
    set /a ISSUES+=1
    goto skip_env
)

REM Check UTF-8 (findstr succeeds means readable ASCII text)
findstr /R "[0-9a-zA-Z]" "%ROOT%.env" >nul 2>&1
if not errorlevel 1 (
    echo    OK .env is readable ASCII/UTF-8
) else (
    echo    BAD .env may be UTF-16LE encoding
    echo      Fix with PowerShell:
    echo        ^(Get-Content .env^) ^| Set-Content -Encoding utf8 .env
    set /a ISSUES+=1
)

REM Check for LLM key
findstr /B "ANTHROPIC_API_KEY=" "%ROOT%.env" >nul 2>&1
if not errorlevel 1 (
    echo    OK ANTHROPIC_API_KEY is set
) else (
    findstr /B "MINIMAX_API_KEY=" "%ROOT%.env" >nul 2>&1
    if not errorlevel 1 (
        echo    OK MINIMAX_API_KEY is set
    ) else (
        echo    MISSING LLM key
        echo      Add one of:
        echo        ANTHROPIC_API_KEY=sk-ant-api03-...
        echo        MINIMAX_API_KEY=sk-cp-...
        set /a ISSUES+=1
    )
)

:skip_env

REM ------------------------------------------------------------------------
REM 2. Python venv check
REM ------------------------------------------------------------------------
echo.
echo [2] Python venv check:
if not "%PYTHON%"=="" (
    echo    OK Python: %PYTHON%
) else (
    echo    MISSING Python
    echo      Run: cd src\ikigai ^&^& uv sync
    set /a ISSUES+=1
    goto skip_venv
)

REM Test critical packages
"%PYTHON%" -c "import langgraph_cli" 2>nul
if errorlevel 1 (
    echo    BAD langgraph-cli missing
    echo      Run: cd src\ikigai ^&^& uv pip install "langgraph-cli[inmem]" langgraph-checkpoint-sqlite colorama
    set /a ISSUES+=1
) else (
    echo    OK langgraph-cli installed
)

"%PYTHON%" -c "import langchain_openai" 2>nul
if errorlevel 1 (
    echo    INFO langchain-openai not installed ^(ok if using Anthropic only^)
) else (
    echo    OK langchain-openai installed
)

"%PYTHON%" -c "import langgraph" 2>nul
if errorlevel 1 (
    echo    BAD langgraph missing
    echo      Run: cd src\ikigai ^&^& uv sync
    set /a ISSUES+=1
) else (
    echo    OK langgraph installed
)

:skip_venv

REM ------------------------------------------------------------------------
REM 3. Critical code files
REM ------------------------------------------------------------------------
echo.
echo [3] Code files check:
if exist "%ROOT%src\ikigai\scripts\sitecustomize.py" (
    echo    OK sitecustomize.py exists ^(OPEN-2 patch survival^)
) else (
    echo    MISSING src\ikigai\scripts\sitecustomize.py
    echo      Re-run Tier 2 commit
    set /a ISSUES+=1
)

if exist "%ROOT%langgraph.json" (
    echo    OK langgraph.json exists
) else (
    echo    MISSING langgraph.json
    set /a ISSUES+=1
)

REM ------------------------------------------------------------------------
REM 4. Report
REM ------------------------------------------------------------------------
echo.
echo ============================================================
if %ISSUES% EQU 0 (
    echo  STATUS: ALL CHECKS PASSED
    echo  Next:  td-chat-server.bat
    echo          td-chat-client.bat  ^(in another terminal^)
) else (
    echo  STATUS: %ISSUES% issue^(s^) found - fix the items above
)
echo ============================================================
echo.

endlocal
