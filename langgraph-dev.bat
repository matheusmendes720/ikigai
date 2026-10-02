@echo off
setlocal

REM langgraph-dev.bat
REM Sobe o LangGraph dev server (porta 2024) com o MCP server do ikigai
REM registrado como tool provider para os graphs.

set "ROOT=%~dp0"
cd /d "%ROOT%"

REM PYTHONPATH igual ao .mcp.json — cobre contracts/ + ikigai/src.
REM scripts/ vem PRIMEIRO para que Python encontre sitecustomize.py
REM (patch de Mount() langgraph_api — sobrevive uv sync). Ver OPEN-2.
set "PYTHONPATH=%ROOT%src\ikigai\scripts;%ROOT%src;%ROOT%src\ikigai\src"

REM Preferir venv do ikigai; fallback para system python
set "PYTHON="
if exist "%ROOT%src\ikigai\.venv\Scripts\python.exe" set "PYTHON=%ROOT%src\ikigai\.venv\Scripts\python.exe"
if "%PYTHON%"=="" (
    where python >nul 2>&1 && set "PYTHON=python"
)
if "%PYTHON%"=="" (
    echo [langgraph-dev] ERROR: no Python found. Run 'uv sync' first.
    exit /b 1
)

echo.
echo ============================================================
echo  Life-OSS ^|^| langgraph dev
echo  Root:    %ROOT%
echo  Python:  %PYTHON%
echo  Graphs:  ikigai_maintainer_v2, ikigai_fork_smoke, ikigai_taskdog_mcp
echo  Studio:  http://localhost:2024  (open in browser for chat UI)
echo  MCP:     ikigai server on stdio (registered in .mcp.json)
echo ============================================================
echo.

REM -m langgraph_cli dev: starts the dev server with hot-reload + Studio
"%PYTHON%" -m langgraph_cli dev %*
