@echo off
chcp 65001 >nul
REM Docker部署启动脚本
REM 自动初始化环境配置并启动服务

echo 🚀 AI-CodeReview 代码审查系统 - Docker部署脚本
echo ==================================

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未安装
    echo.
    echo 🔧 Windows系统Docker安装选项：
    echo    1. 自动下载Docker Desktop安装包
    echo    2. 手动安装Docker Desktop
    echo    3. 退出
    echo.
    set /p choice="请选择 (1-3): "
    
    if "%choice%"=="1" (
        goto :install_docker
    ) else if "%choice%"=="2" (
        echo.
        echo 📝 请手动下载并安装Docker Desktop:
        echo    https://www.docker.com/products/docker-desktop
        echo.
        echo 安装完成后请重新运行此脚本
        pause
        exit /b 1
    ) else (
        exit /b 1
    )
)

REM 检查Docker Compose是否可用
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose未安装或不可用
        echo.
        echo 💡 建议解决方案：
        echo    1. 确保Docker Desktop已完全启动
        echo    2. 重新安装Docker Desktop
        echo    3. 检查Docker Desktop设置中是否启用了Compose
        echo.
        pause
        exit /b 1
    ) else (
        echo ✅ 使用docker-compose命令
        set "COMPOSE_CMD=docker-compose"
    )
) else (
    echo ✅ 使用docker compose命令
    set "COMPOSE_CMD=docker compose"
)

goto :main

:install_docker
echo.
echo 🔧 开始下载Docker Desktop安装包...
echo ⚠️  这可能需要几分钟时间，请耐心等待...

REM 创建临时目录
if not exist "%TEMP%\docker_installer" mkdir "%TEMP%\docker_installer"

REM 下载Docker Desktop安装包
echo 📥 正在下载Docker Desktop...
powershell -Command "try { Invoke-WebRequest -Uri 'https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe' -OutFile '%TEMP%\docker_installer\DockerDesktopInstaller.exe' -UseBasicParsing; Write-Host '✅ 下载完成' } catch { Write-Host '❌ 下载失败:', $_.Exception.Message; exit 1 }"

if errorlevel 1 (
    echo.
    echo ❌ 下载失败，请手动下载安装：
    echo    https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo.
echo 🚀 启动Docker Desktop安装程序...
start /wait "%TEMP%\docker_installer\DockerDesktopInstaller.exe"

echo.
echo ✅ Docker Desktop安装程序已运行
echo.
echo ⚠️  重要提示：
echo    1. 请按照安装向导完成Docker Desktop安装
echo    2. 安装完成后重启计算机（如果需要）
echo    3. 启动Docker Desktop并等待完全加载
echo    4. 然后重新运行此脚本
echo.

REM 清理临时文件
if exist "%TEMP%\docker_installer" rmdir /s /q "%TEMP%\docker_installer"

pause
exit /b 0

:main

REM 创建必要的目录
echo 📁 创建必要目录...
if not exist "data" mkdir data
if not exist "log" mkdir log
if not exist "data\svn" mkdir data\svn
if not exist "conf" mkdir conf

REM 初始化环境配置
echo 🔧 初始化环境配置...
if not exist "conf\.env" (
    if exist "conf\.env.dist" (
        echo 📋 从模板创建.env文件...
        copy "conf\.env.dist" "conf\.env" >nul
        echo ✅ 已创建conf\.env文件
    ) else (
        echo ⚠️ 未找到.env.dist模板，将在容器内自动创建
    )
) else (
    echo ✅ .env文件已存在
)

REM 显示配置提示
if exist "conf\.env" (
    echo.
    echo 📝 重要提示:
    echo    请编辑 conf\.env 文件，配置你的API密钥
    echo    主要配置项：
    echo    - LLM_PROVIDER: 选择AI服务商 ^(deepseek推荐^)
    echo    - DEEPSEEK_API_KEY: DeepSeek API密钥
    echo    - GITLAB_ACCESS_TOKEN: GitLab访问令牌^(可选^)
    echo.
    
    REM 检查是否需要用户配置
    findstr /C:"DEEPSEEK_API_KEY=" conf\.env | findstr /C:"DEEPSEEK_API_KEY=$" >nul
    if not errorlevel 1 (
        echo ⚠️ 检测到API密钥未配置，请先配置后再启动：
        echo    1. 编辑文件: notepad conf\.env
        echo    2. 设置API密钥: DEEPSEEK_API_KEY=your_api_key_here
        echo    3. 然后运行: %~nx0 --start
        echo.
        
        if not "%1"=="--start" if not "%1"=="--force" (
            echo 💡 如果你已经配置完成，使用 --start 参数启动服务
            pause
            exit /b 0
        )
    )
)

REM 检查docker-compose.yml文件
echo 🔍 检查docker-compose.yml文件...
if not exist "docker-compose.yml" (
    echo ⚠️ 未找到docker-compose.yml文件
    echo 📥 正在从GitHub下载...
    
    REM 检查curl是否可用
    curl --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ curl未安装，尝试使用PowerShell下载...
        powershell -Command "try { Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main/docker-compose.yml' -OutFile 'docker-compose.yml' -UseBasicParsing; Write-Host '✅ docker-compose.yml下载成功' } catch { Write-Host '❌ 下载失败:', $_.Exception.Message; exit 1 }"
        if errorlevel 1 (
            echo.
            echo ❌ 自动下载失败，请手动下载：
            echo    1. 访问: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB
            echo    2. 下载docker-compose.yml文件到当前目录
            echo    3. 然后重新运行此脚本
            pause
            exit /b 1
        )
    ) else (
        curl -L -o docker-compose.yml https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main/docker-compose.yml
        if errorlevel 1 (
            echo ❌ 下载失败，请检查网络连接或手动下载
            echo 📝 手动下载地址: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB
            pause
            exit /b 1
        )
        echo ✅ docker-compose.yml下载成功
    )
) else (
    echo ✅ docker-compose.yml文件已存在
)

REM 启动服务
echo 🐳 启动Docker服务...
echo 使用命令: %COMPOSE_CMD%
%COMPOSE_CMD% up -d

echo.
echo ✅ 服务启动完成！
echo.
echo 🌐 访问地址:
echo    - API服务: http://localhost:5001
echo    - 仪表板: http://localhost:5002
echo.
echo 📊 查看服务状态:
echo    %COMPOSE_CMD% ps
echo.
echo 📝 查看日志:
echo    %COMPOSE_CMD% logs -f
echo.
echo 🛑 停止服务:
echo    %COMPOSE_CMD% down

pause
