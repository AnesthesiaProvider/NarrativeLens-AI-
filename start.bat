@echo off
setlocal enabledelayedexpansion
title NarrativeLens AI - Backend Server

echo ===============================================================================
echo                      NarrativeLens AI - Backend Server
echo ===============================================================================
echo.

:: Determine project root and backend directories
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

if exist "%ROOT_DIR%\backend\app\main.py" (
    set "BACKEND_DIR=%ROOT_DIR%\backend"
) else if exist "%ROOT_DIR%\app\main.py" (
    set "BACKEND_DIR=%ROOT_DIR%"
) else (
    echo [ERROR] Could not locate backend application directory.
    echo Looked for: "%ROOT_DIR%\backend\app\main.py"
    pause
    exit /b 1
)

:: Locate virtual environment
set "VENV_ACTIVATE="
if exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=%BACKEND_DIR%\venv\Scripts\activate.bat"
) else if exist "%ROOT_DIR%\venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=%ROOT_DIR%\venv\Scripts\activate.bat"
) else if exist "%BACKEND_DIR%\.venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=%BACKEND_DIR%\.venv\Scripts\activate.bat"
)

if "%VENV_ACTIVATE%"=="" (
    echo [WARNING] No virtual environment found in backend\venv or venv.
    echo Attempting to run with system Python...
) else (
    echo [INFO] Activating virtual environment:
    echo        %VENV_ACTIVATE%
    call "%VENV_ACTIVATE%"
    if errorlevel 1 (
        echo [ERROR] Failed to activate virtual environment.
        pause
        exit /b 1
    )
)

:: Move into backend working directory
cd /d "%BACKEND_DIR%"

:: Check port 8000 availability
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8000 is already in use by another process!
    echo If this is an existing NarrativeLens instance, terminate it before starting a new one.
    echo.
)

:: Check Ollama status (optional LLM arbiter)
curl -s --connect-timeout 2 http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [INFO] Ollama service not detected at http://127.0.0.1:11434.
    echo        (Optional: LLM Context Arbiter will use fallback heuristics if Ollama is offline)
) else (
    echo [INFO] Ollama LLM service detected and active.
)

echo.
echo [INFO] Starting FastAPI server on http://0.0.0.0:8000 (reload enabled)...
echo [INFO] Swagger API Docs will be available at: http://127.0.0.1:8000/docs
echo [INFO] Health Endpoint: http://127.0.0.1:8000/api/health
echo ===============================================================================
echo Press Ctrl+C in this console to stop the backend.
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

if errorlevel 1 (
    echo.
    echo [ERROR] Backend server stopped unexpectedly with error code %errorlevel%.
    pause
)
