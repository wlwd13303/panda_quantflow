@echo off
chcp 65001 >nul
title Panda QuantFlow

echo ========================================================
echo   Panda QuantFlow - single process
echo ========================================================
echo.

cd /d "%~dp0"

set "SERVER_PORT=19081"

echo [1/3] Checking frontend build...
if not exist "src\panda_web_react\dist\" (
    echo    First run, building frontend...
    cd src\panda_web_react
    call npm install
    call npm run build
    cd /d "%~dp0"
    if not exist "src\panda_web_react\dist\" (
        echo   [ERROR] Frontend build failed
        pause
        exit /b 1
    )
) else (
    echo    Frontend build exists, skipping
)

echo [2/3] Starting backend...
echo.
echo ========================================================
echo   Backend API:  http://localhost:%SERVER_PORT%
echo   Frontend:     http://localhost:%SERVER_PORT%/quantflow/
echo ========================================================
echo.
echo   Press Ctrl+C to stop
echo ========================================================
echo.

python -m uvicorn panda_server.main:app --app-dir src --host 0.0.0.0 --port %SERVER_PORT%

pause