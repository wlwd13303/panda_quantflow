@echo off
chcp 65001 >nul
echo ================================
echo   PandaAI QuantFlow - React 版
echo ================================
echo   同时启动前后端服务器
echo ================================
echo.

cd /d "%~dp0"

echo [1/5] 检查 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未安装 Python，请先安装 Python
    pause
    exit /b 1
)
python --version
echo.

echo [2/5] 检查 Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未安装 Node.js，请先安装 Node.js
    pause
    exit /b 1
)
node --version
echo.

echo [3/5] 检查前端依赖...
if not exist "node_modules\" (
    echo 📦 首次运行，正在安装前端依赖...
    call npm install
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo ✅ 前端依赖已安装
)
echo.

echo [4/5] 启动后端服务器...
echo 🔧 后端将在 http://localhost:8000 启动
cd /d "%~dp0\..\.."
start "PandaAI-后端" cmd /k "python 快速启动回测平台.py --no-browser"
echo ✅ 后端服务器已在新窗口启动
echo.

echo [5/5] 启动前端开发服务器...
cd /d "%~dp0"
echo 🚀 前端将在 http://localhost:3000 启动
echo 📡 后端 API 地址: http://localhost:8000
echo.
echo 💡 提示：
echo   - 前端窗口：当前窗口
echo   - 后端窗口：已打开的新窗口
echo   - 关闭任一窗口即停止对应服务
echo.
echo 按 Ctrl+C 停止前端服务器
echo.

call npm run dev

pause

