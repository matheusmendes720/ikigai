@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM td-chat-server.bat — start the IKIGAI taskdog langgraph dev server
REM
REM Endpoints after start:
REM   - API:           http://127.0.0.1:2027
REM   - Studio UI:     https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2027
REM   - API Docs:      http://127.0.0.1:2027/docs
REM
REM Usage:
REM   td-chat-server.bat
REM   td-chat-server.bat --port 2028         (custom port)
REM   set LLM_PROVIDER=anthropic && td-chat-server.bat
REM   set LLM_PROVIDER=minimax   && td-chat-server.bat
REM ============================================================================

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ============================================================
echo  Life-OSS ^| td chat dev server
echo  Root:    %ROOT%
echo ============================================================

REM ------------------------------------------------------------------------
REM 1. Validate .env exists and is UTF-8 (not UTF-16LE which breaks langgraph)
REM ------------------------------------------------------------------------
if not exist "%ROOT%.env" (
    echo [td-chat-server] ERROR: .env not found at %ROOT%.env
    echo   Create it with: MINIMAX_API_KEY=sk-... or ANTHROPIC_API_KEY=sk-ant-...
    exit /b 1
)

REM Detect UTF-16LE (every other byte is 0x00)
findstr /R "[0-9a-zA-Z]" "%ROOT%.env" >nul 2>&1
if errorlevel 1 (
    echo [td-chat-server] ERROR: .env appears to be UTF-16LE encoding.
    echo   Convert to UTF-8 with:  ^(Get-Content .env^) ^| Set-Content -Encoding utf8 .env
    exit /b 1
)

REM ------------------------------------------------------------------------
REM 2. Validate Python venv exists
REM ------------------------------------------------------------------------
set "PYTHON="
if exist "%ROOT%src\ikigai\.venv\Scripts\python.exe" set "PYTHON=%ROOT%src\ikigai\.venv\Scripts\python.exe"
if "%PYTHON%"=="" (
    where python >nul 2>&1 && set "PYTHON=python"
)
if "%PYTHON%"=="" (
    echo [td-chat-server] ERROR: no Python found. Run 'uv sync' in src\ikigai first.
    exit /b 1
)

REM ------------------------------------------------------------------------
REM 3. Check critical packages are installed
REM ------------------------------------------------------------------------
"%PYTHON%" -c "import langgraph_cli" 2>nul
if errorlevel 1 (
    echo [td-chat-server] Installing langgraph-cli...
    cd /d "%ROOT%src\ikigai"
    "%PYTHON%" -m pip install "langgraph-cli[inmem]" langgraph-checkpoint-sqlite colorama 2>nul
    if errorlevel 1 (
        echo [td-chat-server] ERROR: failed to install langgraph-cli. Run 'uv pip install langgraph-cli[inmem]' in src\ikigai manually.
        exit /b 1
    )
    cd /d "%ROOT%"
)

REM ------------------------------------------------------------------------
REM 4. Detect LLM provider based on env vars
REM ------------------------------------------------------------------------
set "PROVIDER=%LLM_PROVIDER%"

REM Auto-detect if not explicitly set
if "%PROVIDER%"=="" (
    REM Check if ANTHROPIC_API_KEY is set AND MINIMAX is not
    for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%ROOT%.env' | Select-String -Pattern 'ANTHROPIC_API_KEY\s*=' | Select-Object -First 1) -match '\S'" 2^>nul') do set "HAS_ANTHROPIC=%%A"
    for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%ROOT%.env' | Select-String -Pattern 'MINIMAX_API_KEY\s*=' | Select-Object -First 1) -match '\S'" 2^>nul') do set "HAS_MINIMAX=%%A"
    if defined HAS_ANTHROPIC if not defined HAS_MINIMAX set "PROVIDER=anthropic"
    if not defined HAS_ANTHROPIC if defined HAS_MINIMAX set "PROVIDER=minimax"
    if defined HAS_ANTHROPIC if defined HAS_MINIMAX set "PROVIDER=minimax (anthropic also set)"
)

if "%PROVIDER%"=="" (
    echo [td-chat-server] WARNING: no LLM provider detected in .env
    echo   Set either:
    echo     ANTHROPIC_API_KEY=sk-ant-api03-...      REM real Claude
    echo     MINIMAX_API_KEY=sk-cp-...                REM MiniMax proxy
    echo.
    echo   Server will start but chat will fail until you set a key.
    set "PROVIDER=none"
)

echo  Provider: %PROVIDER%
echo  Python:   %PYTHON%

REM ------------------------------------------------------------------------
REM 5. Set env vars for dev server
REM ------------------------------------------------------------------------

REM PYTHONPATH: scripts/ first (so sitecustomize.py is found before venv
REM site-packages), then src/ + src/ikigai/src/ for contracts + agents
set "PYTHONPATH=%ROOT%src\ikigai\scripts;%ROOT%src;%ROOT%src\ikigai\src"

REM Disable colors on Windows (ConsoleRenderer needs colorama + it can
REM still cause issues). LOG_JSON=true gives clean structured output.
set "LOG_COLOR=false"
set "LOG_JSON=true"

REM ------------------------------------------------------------------------
REM 6. Start server
REM ------------------------------------------------------------------------
echo ============================================================
echo  Starting langgraph dev server on port 2027 (or from %%*)...
echo  Logs:  C:\Users\mathe\AppData\Local\Temp\claude\...\.output
echo  Stop:  Ctrl+C
echo ============================================================
echo.

"%PYTHON%" -m langgraph_cli dev %*
