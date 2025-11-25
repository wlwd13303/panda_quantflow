@echo off
chcp 65001 >nul
title Panda QuantFlow Launcher

echo ========================================================
echo   Panda QuantFlow 启动脚本
echo ========================================================
echo.

:: 1. 启动后端
echo [1/2] 正在启动后端服务...
start "Panda Backend" cmd /k "python -m uvicorn panda_server.main:app --app-dir src --host 0.0.0.0 --port 8000"

:: 2. 启动前端
echo [2/2] 正在启动前端服务...
cd src\panda_web_react
start "Panda Frontend" cmd /k "npm run dev"

echo.
echo ✅ 所有服务已启动！
echo    请检查弹出的两个命令行窗口以查看运行日志。
echo.
pause
