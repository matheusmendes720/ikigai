@echo off
REM langgraph-bg.bat
REM Sobe langgraph dev em background (processo detached).
REM Uso:
REM   start "" "C:\...\langgraph-bg.bat"
REM Depois acesse http://localhost:2024 no navegador.

set "ROOT=%~dp0"
cd /d "%ROOT%"

REM scripts/ vem PRIMEIRO para que Python encontre sitecustomize.py
REM (patch de Mount() langgraph_api — sobrevive uv sync). Ver OPEN-2.
set "PYTHONPATH=%ROOT%src\ikigai\scripts;%ROOT%src;%ROOT%src\ikigai\src"

set "PYTHON="
if exist "%ROOT%src\ikigai\.venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%src\ikigai\.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1 && set "PYTHON=python"
)

if "%PYTHON%"=="" (
    echo [langgraph-bg] ERROR: Python nao encontrado.
    exit /b 1
)

echo [langgraph-bg] Subindo langgraph dev em background...
echo [langgraph-bg] Logs: %ROOT%.langgraph\logs\dev.log

REM Inicia o servidor via cmd /c start (realmente detached)
REM /B = mesmo console (mas processo fica independente)
start /B "langgraph-dev" cmd /c ""%PYTHON%" -m langgraph_cli dev %* > "%ROOT%.langgraph\logs\dev.log" 2>&1"

echo [langgraph-bg] Servidor lancado. Aguarde 10-15s e abra http://localhost:2024
echo [langgraph-bg] Para parar: taskkill /F /IM python.exe (cuidado: mata todos os python)
exit /b 0
