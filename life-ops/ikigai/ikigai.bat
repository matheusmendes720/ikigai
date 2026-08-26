@echo off
setlocal

set "IKIGAI_ROOT=%~dp0"
set "PYTHON=%IKIGAI_ROOT%.venv\Scripts\python.exe"
set "PYTHONPATH=%IKIGAI_ROOT%src"

cd /d "%IKIGAI_ROOT%"

if "%~1"=="" goto help
if "%~1"=="mcp"        goto mcp
if "%~1"=="agent"      goto agent
if "%~1"=="chat"       goto chat
if "%~1"=="list"       goto list
if "%~1"=="run"        goto run
if "%~1"=="checkpoint"  goto checkpoint
goto help

:mcp
    "%PYTHON%" run_mcp_server.py %2 %3 %4 %5
    exit /b

:agent
    set "THREAD=%2"
    if "%THREAD%"=="" set "THREAD=default"
    "%PYTHON%" -m agents.deepagents_harness --thread %THREAD% %3 %4 %5 %6 %7
    exit /b

:chat
    set "THREAD=%2"
    if "%THREAD%"=="" set "THREAD=default"
    "%PYTHON%" -m agents.deepagents_harness --thread %THREAD% --chat
    exit /b

:list
    "%PYTHON%" -m agents.deepagents_harness --list-checkpoints
    exit /b

:run
    set "THREAD=%2"
    if "%THREAD%"=="" set "THREAD=default"
    "%PYTHON%" -m agents.deepagents_harness --thread %THREAD%
    exit /b

:checkpoint
    "%PYTHON%" -m agents.deepagents_harness --list-checkpoints
    exit /b

:help
    echo IKIGAi Deep Agents Launcher
    echo.
    echo Usage:
    echo   ikigai.bat mcp           Start MCP server (stdio)
    echo   ikigai.bat agent         Run one cycle (default thread)
    echo   ikigai.bat agent ^<thread^>
    echo   ikigai.bat chat          Start chat REPL (default thread)
    echo   ikigai.bat chat ^<thread^>
    echo   ikigai.bat list          List checkpoints
    echo   ikigai.bat run ^<thread^> Run one cycle
    echo   ikigai.bat checkpoint    List checkpoints
    exit /b
