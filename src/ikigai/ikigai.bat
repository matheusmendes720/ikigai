@echo off
setlocal

set "IKIGAI_ROOT=%~dp0"
REM Both the poetry-src layout (ikigai/mcp_server/agents/...) AND the
REM sibling packages (contracts, mesh) live at ..\..\src (life/src).
set "PYTHONPATH=%IKIGAI_ROOT%src;%IKIGAI_ROOT%..\..\src"

cd /d "%IKIGAI_ROOT%"

REM Prefer project-local .venv; fall back to system python (if on PATH).
set "PYTHON="
if exist "%IKIGAI_ROOT%.venv\Scripts\python.exe" set "PYTHON=%IKIGAI_ROOT%.venv\Scripts\python.exe"
if "%PYTHON%"=="" (
    where python >nul 2>&1 && set "PYTHON=python"
)
if "%PYTHON%"=="" (
    echo [ikigai] ERROR: no Python found. Run 'uv sync' first or install Python 3.10+.
    exit /b 1
)

REM No subcommand → help
if "%~1"=="" goto help

REM Deep Agent subcommands
if "%~1"=="chat"      goto chat
if "%~1"=="agent"     goto agent
if "%~1"=="run"       goto run
if "%~1"=="list"      goto list
if "%~1"=="checkpoint" goto checkpoint

REM MCP server
if "%~1"=="mcp"       goto mcp

REM Gateway management
if "%~1"=="gateway"   goto gateway
if "%~1"=="gw"        goto gateway

REM Event log inspection
if "%~1"=="events"    goto events
if "%~1"=="event"     goto events
if "%~1"=="ev"        goto events

REM SSE consumer
if "%~1"=="sse"       goto sse
if "%~1"=="watch"     goto sse

REM Backend mgmt (start/stop/status of gateway daemon)
if "%~1"=="backend"   goto backend

goto help

:chat
    set "THREAD=%~2"
    if "%THREAD%"=="" set "THREAD=default"
    "%PYTHON%" -m agents.deepagents_harness --thread %THREAD% --chat
    exit /b

:agent
    set "THREAD=%~2"
    if "%THREAD%"=="" set "THREAD=default"
    "%PYTHON%" -m agents.deepagents_harness --thread %THREAD% %3 %4 %5 %6 %7
    exit /b

:run
    set "THREAD=%~2"
    if "%THREAD%"=="" set "THREAD=default"
    "%PYTHON%" -m agents.deepagents_harness --thread %THREAD%
    exit /b

:list
    "%PYTHON%" -m agents.deepagents_harness --list-checkpoints
    exit /b

:checkpoint
    "%PYTHON%" -m agents.deepagents_harness --list-checkpoints
    exit /b

:mcp
    REM Start MCP server (stdio transport, JSON-RPC 2.0).
    "%PYTHON%" -m mcp_server.server
    exit /b

:gateway
    REM gateway start | stop | status | restart | pid | log
    if "%~2"=="" (
        "%PYTHON%" -m ikigai.gateway.start_gateway --help
        exit /b
    )
    "%PYTHON%" -m ikigai.gateway.start_gateway %2 %3 %4 %5 %6
    exit /b

:events
    REM events tail | status | since <duration> | show <id>
    if "%~2"=="" (
        "%PYTHON%" -m ikigai.gateway.event_log_cli --help
        exit /b
    )
    "%PYTHON%" -m ikigai.gateway.event_log_cli %2 %3 %4 %5 %6 %7
    exit /b

:sse
    REM sse watch [--filter <name>] [--duration <sec>]
    "%PYTHON%" -m ikigai.gateway.client_cli %2 %3 %4 %5 %6 %7
    exit /b

:backend
    REM backend status | tail-log
    if "%~2"=="status" (
        "%PYTHON%" -m ikigai.gateway.event_log_cli status
        exit /b
    )
    if "%~2"=="tail" (
        "%PYTHON%" -m ikigai.gateway.event_log_cli tail
        exit /b
    )
    "%PYTHON%" -m ikigai.gateway.event_log_cli status
    exit /b

:help
    echo.
    echo IKIGAi Command Palette  (single CLI for deep agents, MCP, gateway, SSE)
    echo ======================================================================
    echo.
    echo Usage:  ikigai.bat ^<command^> [args]
    echo.
    echo Deep Agent (carro-chefe):
    echo   ikigai.bat chat ^<thread^>          Start chat REPL (default thread: 'default')
    echo   ikigai.bat agent ^<thread^>         Single-shot invocation
    echo   ikigai.bat run ^<thread^>           Alias for 'agent'
    echo   ikigai.bat list                    List checkpoints
    echo   ikigai.bat checkpoint              Alias for 'list'
    echo.
    echo MCP server:
    echo   ikigai.bat mcp                     Start MCP server (stdio, JSON-RPC 2.0)
    echo.
    echo Backend Gateway management:
    echo   ikigai.bat gateway start           Start gateway daemon (background)
    echo   ikigai.bat gateway stop            Stop gateway daemon
    echo   ikigai.bat gateway restart         Restart gateway daemon
    echo   ikigai.bat gateway status          Show gateway PID + state
    echo   ikigai.bat gateway pid             Print PID only
    echo   ikigai.bat gateway log             Tail gateway log
    echo.
    echo Event log inspection:
    echo   ikigai.bat events tail             Live tail of events.jsonl
    echo   ikigai.bat events status           Show event log path + size
    echo   ikigai.bat events since ^<dur^>     Events since duration (e.g. 30m, 2h)
    echo   ikigai.bat events show ^<id^>       Show event by ID
    echo.
    echo SSE consumer:
    echo   ikigai.bat sse watch               Live-stream gateway /events
    echo   ikigai.bat sse watch --filter ^<name^>   Filter by event name (taskdog, tuiboard, ...)
    echo   ikigai.bat sse watch --duration ^<sec^>  Auto-exit after N seconds
    echo.
    echo Backend status (shortcuts):
    echo   ikigai.bat backend status          Show gateway status
    echo   ikigai.bat backend tail            Tail event log
    echo.
    echo Notes:
    echo   - PYTHONPATH=src is set automatically; no manual env var needed.
    echo   - PowerShell users can use:  .\ikigai.ps1 ^<command^> [args]
    echo   - All subcommands accept --help for full options.
    echo.
    exit /b 0
