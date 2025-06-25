@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM AI-CodeReview-Gitlab 智能启动脚本 (Windows)
REM 支持多容器和单容器模式选择

echo.
echo 🎯 AI-CodeReview-Gitlab 智能启动助手
echo 版本: 2.0 ^| 支持多容器/单容器部署
echo.

REM 检查 Docker 环境
:check_docker
echo [INFO] 检查 Docker 环境...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker 未安装，请选择安装选项
    goto install_menu
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Docker Compose 未安装，请选择安装选项
        goto install_menu
    )
)

echo [SUCCESS] Docker 环境检查通过
goto check_files

REM 安装菜单
:install_menu
echo.
echo 🔧 环境安装选项：
echo 1) 下载 Docker Desktop for Windows
echo 2) 继续使用现有环境
echo 0) 退出
echo.
set /p install_choice="请选择 [1-2, 0]: "

if "%install_choice%"=="1" (
    echo [INFO] 正在打开 Docker Desktop 下载页面...
    start https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe
    echo [INFO] 请下载并安装 Docker Desktop，然后重新运行此脚本
    pause
    exit /b 0
)

if "%install_choice%"=="2" (
    echo [WARNING] 继续使用，但可能因缺少 Docker 而失败
    goto check_files
)

if "%install_choice%"=="0" exit /b 0

echo [WARNING] 无效选择
goto install_menu

REM 检查配置文件
:check_files
echo [INFO] 检查配置文件...
call :download_compose_files

REM 创建必要目录
:create_directories
echo [INFO] 创建必要目录...
if not exist "conf" mkdir conf
if not exist "data" mkdir data
if not exist "log" mkdir log
if not exist "data\svn" mkdir data\svn
echo [SUCCESS] 目录创建完成

REM 主菜单循环
:main_menu
echo.
echo 🚀 AI-CodeReview-Gitlab 部署模式选择
echo ==================================================
echo 1) 多容器模式 (推荐生产环境)
echo    - 基础版：仅启动 API + UI 服务
echo    - 完整版：启动 API + UI + Worker + Redis
echo.
echo 2) 单容器模式 (适合开发测试)
echo    - 所有服务在一个容器中运行
echo    - 可选启用 Redis 支持
echo.
echo 3) 停止所有服务
echo.
echo 4) 查看服务状态
echo.
echo 5) 查看服务日志
echo.
echo 6) 安装/更新环境
echo    - 下载 Docker Desktop for Windows
echo    - 下载最新配置文件
echo.
echo 7) 下载配置文件
echo    - 下载/更新 docker-compose.yml
echo    - 下载/更新相关配置
echo.
echo 0) 退出
echo ==================================================

set /p choice="请选择操作 [0-7]: "

if "%choice%"=="1" goto multi_container_menu
if "%choice%"=="2" goto single_container_menu
if "%choice%"=="3" goto stop_services
if "%choice%"=="4" goto show_status
if "%choice%"=="5" goto show_logs
if "%choice%"=="6" goto install_environment
if "%choice%"=="7" goto download_files
if "%choice%"=="0" goto exit_script

echo [WARNING] 无效选择，请重新输入
goto main_menu

REM 安装环境选项
:install_environment
echo [INFO] 开始安装/更新环境...
echo [INFO] 正在打开 Docker Desktop 下载页面...
start https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe
echo [INFO] 下载配置文件...
call :download_compose_files
echo [SUCCESS] 环境安装/更新完成
echo [INFO] 请安装 Docker Desktop 后重新运行此脚本
goto continue_prompt

REM 下载配置文件选项
:download_files
echo [INFO] 开始下载配置文件...
call :download_compose_files
echo [SUCCESS] 配置文件下载完成
goto continue_prompt

REM 多容器模式菜单
:multi_container_menu
echo.
echo 🔧 多容器模式选项：
echo 1) 基础模式 (仅 API + UI)
echo 2) 完整模式 (API + UI + Worker + Redis)
echo 0) 返回主菜单

set /p sub_choice="请选择 [1-2, 0]: "

if "%sub_choice%"=="1" (
    echo [INFO] 启动多容器基础模式...
    docker-compose up -d
    call :check_health
    goto continue_prompt
)

if "%sub_choice%"=="2" (
    echo [INFO] 启动多容器完整模式...
    set COMPOSE_PROFILES=worker
    docker-compose up -d
    call :check_health
    goto continue_prompt
)

if "%sub_choice%"=="0" goto main_menu

echo [WARNING] 无效选择，请重新选择
goto multi_container_menu

REM 单容器模式菜单
:single_container_menu
echo.
echo 🔧 单容器模式选项：
echo 1) 基础模式 (进程队列)
echo 2) Redis 模式 (包含 Redis 队列)
echo 0) 返回主菜单

set /p sub_choice="请选择 [1-2, 0]: "

if "%sub_choice%"=="1" (
    echo [INFO] 启动单容器基础模式...
    docker-compose -f docker-compose.single.yml up -d
    call :check_health
    goto continue_prompt
)

if "%sub_choice%"=="2" (
    echo [INFO] 启动单容器 Redis 模式...
    set COMPOSE_PROFILES=redis
    docker-compose -f docker-compose.single.yml up -d
    call :check_health
    goto continue_prompt
)

if "%sub_choice%"=="0" goto main_menu

echo [WARNING] 无效选择，请重新选择
goto single_container_menu

REM 停止所有服务
:stop_services
echo [INFO] 停止所有服务...

REM 尝试停止多容器服务
docker-compose ps -q >nul 2>&1
if not errorlevel 1 (
    echo [INFO] 停止多容器服务...
    docker-compose down
)

REM 尝试停止单容器服务
docker-compose -f docker-compose.single.yml ps -q >nul 2>&1
if not errorlevel 1 (
    echo [INFO] 停止单容器服务...
    docker-compose -f docker-compose.single.yml down
)

echo [SUCCESS] 所有服务已停止
goto continue_prompt

REM 查看服务状态
:show_status
echo.
echo [INFO] === 多容器服务状态 ===
docker-compose ps 2>nul || echo 无多容器服务运行

echo.
echo [INFO] === 单容器服务状态 ===
docker-compose -f docker-compose.single.yml ps 2>nul || echo 无单容器服务运行

echo.
echo [INFO] === Docker 容器状态 ===
docker ps --filter "name=ai-codereview" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
goto continue_prompt

REM 查看服务日志
:show_logs
echo.
echo 📋 选择要查看的日志：
echo 1) 多容器服务日志
echo 2) 单容器服务日志
echo 3) 特定容器日志
echo 0) 返回主菜单

set /p log_choice="请选择 [1-3, 0]: "

if "%log_choice%"=="1" (
    echo [INFO] 显示多容器服务日志...
    docker-compose logs -f --tail=100
    goto continue_prompt
)

if "%log_choice%"=="2" (
    echo [INFO] 显示单容器服务日志...
    docker-compose -f docker-compose.single.yml logs -f --tail=100
    goto continue_prompt
)

if "%log_choice%"=="3" (
    echo.
    echo 可用容器：
    docker ps --filter "name=ai-codereview" --format "{{.Names}}"
    echo.
    set /p container_name="请输入容器名称: "
    if not "!container_name!"=="" (
        docker logs -f --tail=100 !container_name!
    ) else (
        echo [WARNING] 容器名称不能为空
    )
    goto continue_prompt
)

if "%log_choice%"=="0" goto main_menu

echo [WARNING] 无效选择
goto show_logs

REM 检查服务健康状态
:check_health
echo [INFO] 检查服务健康状态...

REM 检查 API 服务 (使用 PowerShell 替代 curl)
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5001/health' -UseBasicParsing -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] API 服务 (端口 5001) 运行正常
) else (
    echo [WARNING] API 服务 (端口 5001) 可能未启动或不健康
)

REM 检查 UI 服务
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5002' -UseBasicParsing -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] UI 服务 (端口 5002) 运行正常
) else (
    echo [WARNING] UI 服务 (端口 5002) 可能未启动或不健康
)

echo.
echo 📋 服务访问地址：
echo   • API 服务: http://localhost:5001
echo   • UI 界面:  http://localhost:5002
exit /b 0

REM 继续提示
:continue_prompt
echo.
pause
goto main_menu

REM 下载配置文件函数
:download_compose_files
set BASE_URL=https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main

REM 检查多容器配置
if not exist "docker-compose.yml" (
    echo [INFO] 下载多容器配置文件...
    powershell -Command "try { Invoke-WebRequest -Uri '%BASE_URL%/docker-compose.yml' -OutFile 'docker-compose.yml' } catch { Write-Host '[ERROR] 多容器配置文件下载失败'; exit 1 }"
    if errorlevel 1 (
        echo [ERROR] 多容器配置文件下载失败
        exit /b 1
    )
    echo [SUCCESS] 多容器配置文件下载完成
) else (
    echo [INFO] 多容器配置文件已存在
)

REM 检查单容器配置
if not exist "docker-compose.single.yml" (
    echo [INFO] 下载单容器配置文件...
    powershell -Command "try { Invoke-WebRequest -Uri '%BASE_URL%/docker-compose.single.yml' -OutFile 'docker-compose.single.yml' } catch { Write-Host '[ERROR] 单容器配置文件下载失败'; exit 1 }"
    if errorlevel 1 (
        echo [ERROR] 单容器配置文件下载失败
        exit /b 1
    )
    echo [SUCCESS] 单容器配置文件下载完成
) else (
    echo [INFO] 单容器配置文件已存在
)

REM 检查 Dockerfile
if not exist "Dockerfile" (
    echo [INFO] 下载 Dockerfile...
    powershell -Command "try { Invoke-WebRequest -Uri '%BASE_URL%/Dockerfile' -OutFile 'Dockerfile' } catch { Write-Host '[WARNING] Dockerfile 下载失败，将使用预构建镜像' }"
    if not errorlevel 1 (
        echo [SUCCESS] Dockerfile 下载完成
    )
)

exit /b 0

REM 退出脚本
:exit_script
echo [INFO] 感谢使用 AI-CodeReview-Gitlab!
pause
exit /b 0
