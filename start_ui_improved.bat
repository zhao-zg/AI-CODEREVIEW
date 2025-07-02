@echo off
chcp 65001 >nul 2>&1
REM AI-CodeReview UI启动脚本 - 改进版
REM 支持优雅关闭和进程管理

echo ========================================
echo    AI-CodeReview UI 启动脚本 v2.0
echo ========================================

REM 设置环境变量
set UI_PORT=5002
set UI_HOST=0.0.0.0

REM 检查端口占用
echo 检查端口 %UI_PORT% 是否被占用...
netstat -ano | findstr ":%UI_PORT%" > nul
if %ERRORLEVEL% == 0 (
    echo [WARNING] 端口 %UI_PORT% 已被占用
    echo 正在尝试释放端口...
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%UI_PORT%"') do (
        if not "%%i"=="0" (
            echo 终止进程 PID: %%i
            taskkill /F /PID %%i > nul 2>&1
        )
    )
    timeout /t 2 > nul
    echo [OK] 端口释放完成
)

REM 清理旧的Streamlit进程
echo 清理旧的Streamlit进程...
taskkill /F /IM streamlit.exe > nul 2>&1
timeout /t 1 > nul

REM 检查Python环境
echo 检查Python环境...
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python未正确安装或不在PATH中
    pause
    exit /b 1
)

REM 检查必要的依赖
echo 检查Streamlit是否安装...
python -c "import streamlit" > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Streamlit未安装，正在尝试安装...
    pip install streamlit
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Streamlit安装失败
        pause
        exit /b 1
    )
)

REM 检查UI文件是否存在
if not exist "ui.py" (
    echo [ERROR] ui.py 文件不存在
    pause
    exit /b 1
)

echo.
echo ========================================
echo 启动配置:
echo   UI地址: http://%UI_HOST%:%UI_PORT%
echo   主文件: ui.py
echo   工作目录: %CD%
echo ========================================
echo.
echo 提示: 
echo   - 按 Ctrl+C 优雅关闭服务
echo   - 如果无响应，请关闭此窗口
echo   - 服务启动后会自动打开浏览器
echo.

REM 创建PID文件用于跟踪进程
echo %date% %time% > ui_startup.log

REM 启动Streamlit UI
echo 正在启动 AI-CodeReview UI...
streamlit run ui.py --server.port %UI_PORT% --server.address %UI_HOST% --server.runOnSave false --server.fileWatcherType none --global.suppressDeprecationWarnings true

REM 清理工作
echo.
echo [INFO] UI服务已停止，正在清理...
del ui_startup.log > nul 2>&1
echo [OK] 清理完成

pause
