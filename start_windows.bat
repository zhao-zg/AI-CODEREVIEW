@echo off
REM AI-CodeReview 启动脚本 (Windows 版本)
REM 检查环境配置并运行服务

echo ======================================
echo     AI-CodeReview 启动助手 (Windows)
echo ======================================
echo.

REM 1. 环境配置检查
echo [1/4] 检查环境配置...

REM 优先使用 Python 版本的检查器
python scripts\env_checker.py 2>nul
if errorlevel 1 (
    echo Python 检查器不可用，使用批处理版本...
    call scripts\env_checker.bat
    if errorlevel 1 (
        echo 警告: 环境配置检查存在问题，但将继续启动
    )
) else (
    echo 环境配置检查完成
)
echo.

REM 2. 检查 Docker 是否可用
echo [2/4] 检查 Docker 环境...

docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker 未安装或不可用
    echo 请先安装 Docker Desktop
    pause
    exit /b 1
)

REM 3. 检查 Docker Compose 是否可用
echo [3/4] 检查 Docker Compose...
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo 错误: Docker Compose 未安装或不可用
        pause
        exit /b 1
    ) else (
        echo 使用 docker-compose (经典版本)
    )
) else (
    echo 使用 docker compose (新版本)
)

echo Docker 环境检查通过
echo.

REM 4. 运行主启动脚本
echo [4/4] 启动服务...
REM 尝试使用 WSL 运行 bash 脚本
echo 尝试使用 WSL 运行脚本...
wsl bash start.sh
if errorlevel 1 (
    echo WSL 不可用，尝试使用 Git Bash...
    
    REM 尝试使用 Git Bash
    if exist "C:\Program Files\Git\bin\bash.exe" (
        "C:\Program Files\Git\bin\bash.exe" start.sh
    ) else if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
        "C:\Program Files (x86)\Git\bin\bash.exe" start.sh
    ) else (
        echo 错误: 无法找到 bash 解释器
        echo 请安装以下之一:
        echo 1. Windows Subsystem for Linux (WSL)
        echo 2. Git for Windows
        pause
        exit /b 1
    )
)

pause
