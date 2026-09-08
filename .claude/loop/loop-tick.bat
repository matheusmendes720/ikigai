@echo off
REM Loop Tick — Windows wrapper
REM Calls loop-tick.sh via Git Bash (assuming Git for Windows is installed)

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "COST_CAP=5"
set "MAX_RUNTIME=30"
set "DRY_RUN="
set "GRAPH="

:parse_args
if "%~1"=="" goto :after_args
if "%~1"=="--cost-cap" (
  set "COST_CAP=%~2"
  shift
  shift
  goto :parse_args
)
if "%~1"=="--max-runtime" (
  set "MAX_RUNTIME=%~2"
  shift
  shift
  goto :parse_args
)
if "%~1"=="--dry-run" (
  set "DRY_RUN=--dry-run"
  shift
  goto :parse_args
)
if "%~1"=="--graph" (
  set "GRAPH=--graph %~2"
  shift
  shift
  goto :parse_args
)
echo Unknown arg: %~1
exit /b 1

:after_args
set "ARGS=--cost-cap %COST_CAP% --max-runtime %MAX_RUNTIME%"
if defined DRY_RUN set "ARGS=%ARGS% --dry-run"
if defined GRAPH set "ARGS=%ARGS% %GRAPH%"

REM Try Git Bash first, then WSL bash, then cygwin bash
where bash >nul 2>&1
if %errorlevel% equ 0 (
  bash "%SCRIPT_DIR%loop-tick.sh" %ARGS%
  exit /b %errorlevel%
)

echo ERROR: bash not found. Install Git for Windows or WSL.
exit /b 1
