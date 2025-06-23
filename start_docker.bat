@echo off
chcp 65001 >nul
REM Docker部署启动脚本
REM 自动初始化环境配置并启动服务

echo 🚀 AI-CodeReview 代码审查系统 - Docker部署脚本
echo ==================================

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未安装，请先安装Docker Desktop
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose未安装，请先安装Docker Compose
    pause
    exit /b 1
)

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
docker-compose up -d

echo.
echo ✅ 服务启动完成！
echo.
echo 🌐 访问地址:
echo    - API服务: http://localhost:5001
echo    - 仪表板: http://localhost:5002
echo.
echo 📊 查看服务状态:
echo    docker-compose ps
echo.
echo 📝 查看日志:
echo    docker-compose logs -f
echo.
echo 🛑 停止服务:
echo    docker-compose down

pause
