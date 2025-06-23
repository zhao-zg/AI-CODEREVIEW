@echo off
REM Docker Compose 部署前的环境初始化脚本 (Windows 版本)
REM 自动创建完整的 .env 配置，解决配置不完整的问题

echo 🚀 AI-CodeReview-GitLab Docker Compose 部署前置脚本
echo ===========================================================
echo 📋 解决 docker-compose 部署时 .env 数据不完整的问题
echo ===========================================================

REM 检查 Python 是否可用
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :run_init
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :run_init
)

echo ❌ 未找到 Python 解释器，请安装 Python 3
pause
exit /b 1

:run_init
echo ✅ 找到 Python 解释器: %PYTHON_CMD%

REM 运行环境初始化脚本
echo 🔧 运行环境配置初始化...
%PYTHON_CMD% scripts\init_env.py

if %errorlevel% equ 0 (
    echo.
    echo 🎉 环境初始化完成！现在可以启动 Docker Compose 服务
    echo.
    echo 📋 启动命令:
    echo    # 使用 Docker Hub 镜像 ^(推荐^)
    echo    docker-compose -f docker-compose.dockerhub.yml up -d
    echo.
    echo    # 或使用 GitHub Container Registry 镜像
    echo    docker-compose up -d
    echo.
    echo    # 或本地构建
    echo    docker-compose up --build -d
    echo.
    echo 📖 访问服务:
    echo    - API 服务: http://localhost:5001
    echo    - Web 界面: http://localhost:5002
    echo    - 默认登录: admin / admin123
    echo.
) else (
    echo ❌ 环境初始化失败，请检查错误信息
    pause
    exit /b 1
)

pause
