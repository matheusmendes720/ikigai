@echo off
REM langgraph dev shim — routes to Python 3.13 to avoid protobuf crash on Python 3.14
REM Root cause: Python 3.14 + protobuf (pre-5.0) are incompatible (Metaclasses tp_new crash)
REM Fix: use Python 3.13 which has langgraph-cli 0.4.36 + langgraph-api 0.16.1
REM Usage: langgraph-dev.bat [args...]
REM Or symlink/copy to a directory on PATH

set LANGGRAPH_EXE=C:\Users\mathe\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\langgraph.exe

if not exist "%LANGGRAPH_EXE%" (
    echo ERROR: langgraph.exe not found at:
    echo   %LANGGRAPH_EXE%
    echo Install langgraph-cli on Python 3.13 first:
    echo   py -3.13 -m pip install langgraph-cli
    exit /b 1
)

"%LANGGRAPH_EXE%" %*
