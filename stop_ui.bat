@echo off
chcp 65001 >nul 2>&1
REM AI-CodeReview UI停止脚本
REM 用于强制停止UI服务和相关进程

echo ========================================
echo    AI-CodeReview UI 停止脚本
echo ========================================

echo 正在停止 AI-CodeReview UI 服务...

REM 停止Streamlit进程
echo.
echo 1. 停止Streamlit进程...
tasklist | findstr streamlit.exe > nul
if %ERRORLEVEL% == 0 (
    echo 发现Streamlit进程，正在终止...
    taskkill /F /IM streamlit.exe > nul 2>&1
    if %ERRORLEVEL% == 0 (
        echo [OK] Streamlit进程已停止
    ) else (
        echo [ERROR] 停止Streamlit进程失败
    )
) else (
    echo [INFO] 未发现Streamlit进程
)

REM 停止占用5002端口的进程
echo.
echo 2. 释放端口5002...
netstat -ano | findstr ":5002" > nul
if %ERRORLEVEL% == 0 (
    echo 发现端口5002被占用，正在释放...
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":5002"') do (
        if not "%%i"=="0" (
            echo 终止进程 PID: %%i
            taskkill /F /PID %%i > nul 2>&1
        )
    )
    echo [OK] 端口5002已释放
) else (
    echo [INFO] 端口5002未被占用
)

REM 停止可能的Python UI进程
echo.
echo 3. 检查Python UI进程...
wmic process where "name='python.exe' and commandline like '%%ui.py%%'" get processid /value 2>nul | findstr "ProcessId" > temp_pids.txt
if exist temp_pids.txt (
    for /f "tokens=2 delims==" %%i in (temp_pids.txt) do (
        if not "%%i"=="" (
            echo 终止Python UI进程 PID: %%i
            taskkill /F /PID %%i > nul 2>&1
        )
    )
    del temp_pids.txt
    echo [OK] Python UI进程已清理
) else (
    echo [INFO] 未发现Python UI进程
)

REM 清理临时文件
echo.
echo 4. 清理临时文件...
if exist "ui_startup.log" (
    del ui_startup.log > nul 2>&1
    echo [OK] 清理启动日志
)

if exist ".streamlit" (
    rmdir /s /q .streamlit > nul 2>&1
    echo [OK] 清理Streamlit缓存
)

echo.
echo ========================================
echo [OK] UI服务停止完成
echo ========================================
echo.
echo 如果仍有进程无法停止，请：
echo   1. 打开任务管理器
echo   2. 查找并结束相关的python.exe或streamlit.exe进程
echo   3. 或者重启系统
echo.

pause
