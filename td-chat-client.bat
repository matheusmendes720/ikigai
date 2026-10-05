@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM td-chat-client.bat — start the IKIGAI td chat REPL client
REM
REM Connects to the langgraph dev server (must be running via td-chat-server.bat).
REM Type prompts, get streaming responses from the ReAct agent.
REM
REM Usage:
REM   td-chat-client.bat
REM   td-chat-client.bat --url http://127.0.0.1:2028
REM ============================================================================

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON="
if exist "%ROOT%src\ikigai\.venv\Scripts\python.exe" set "PYTHON=%ROOT%src\ikigai\.venv\Scripts\python.exe"
if "%PYTHON%"=="" (
    where python >nul 2>&1 && set "PYTHON=python"
)
if "%PYTHON%"=="" (
    echo [td-chat-client] ERROR: no Python found.
    exit /b 1
)

REM Check if server is up
set "URL=http://127.0.0.1:2027"
if not "%1"=="" set "URL=%1"

echo [td-chat-client] Checking server at %URL%/info ...
"%PYTHON%" -c "import urllib.request; r = urllib.request.urlopen('%URL%/info', timeout=2); print('[td-chat-client] OK:', r.status)" 2>nul
if errorlevel 1 (
    echo [td-chat-client] ERROR: server not reachable at %URL%
    echo   Start it first with: td-chat-server.bat
    exit /b 1
)
echo.

REM Run the chat REPL
echo ========================================================================
echo  Life-OSS -- td chat client
echo  Server: %URL%
echo  Commands:  /new (new thread) -- /list (list tasks) -- Ctrl+C to quit
echo ========================================================================
echo.

REM Pass the URL to the script
"%PYTHON%" "%ROOT%scripts\taskdog_chat.py" --url "%URL%"
