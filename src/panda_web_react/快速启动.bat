@echo off
chcp 65001 >nul
title Panda QuantFlow ^(快速启动^)

echo ================================
echo   PandaAI QuantFlow - React 版
echo   前后端统一进程
echo ================================
echo.

cd /d "%~dp0"

:: 检查并构建前端
echo [1/3] 检查前端构建产物...
if not exist "dist\" (
    echo   首次运行，正在安装依赖并构建...
    call npm install
    call npm run build
    if not exist "dist\" (
        echo   [错误] 前端构建失败
        pause
        exit /b 1
    )
) else (
    echo   前端已构建，跳过
)

:: 启动后端
echo [2/3] 启动后端...
cd /d "%~dp0\..\.."
echo.
echo ========================================================
echo   浏览器打开: http://localhost:8000/quantflow/
echo   后端 API:   http://localhost:8000
echo ========================================================
echo.
echo   按 Ctrl+C 停止服务
echo ========================================================
echo.

python -m uvicorn panda_server.main:app --app-dir src --host 0.0.0.0 --port 8000

pause
