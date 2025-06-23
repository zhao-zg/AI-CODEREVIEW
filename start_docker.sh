#!/bin/bash
# Docker部署启动脚本
# 自动初始化环境配置并启动服务

set -e

echo "🚀 AI-CodeReview 代码审查系统 - Docker部署脚本"
echo "=================================="

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$NAME
            VER=$VERSION_ID
        else
            OS="Unknown Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
    else
        OS="Unknown"
    fi
    echo "检测到操作系统: $OS"
}

# 安装Docker的函数
install_docker() {
    echo "🔧 开始安装Docker..."
    
    case "$OS" in
        *"Ubuntu"*|*"Debian"*)
            echo "📦 在Ubuntu/Debian系统上安装Docker..."
            # 更新包索引
            sudo apt-get update
            
            # 安装必要的包
            sudo apt-get install -y \
                ca-certificates \
                curl \
                gnupg \
                lsb-release
            
            # 添加Docker官方GPG密钥
            sudo mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            
            # 设置稳定版仓库
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
              $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # 更新包索引
            sudo apt-get update
            
            # 安装Docker Engine
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            
            # 启动Docker服务
            sudo systemctl start docker
            sudo systemctl enable docker
            
            # 将当前用户添加到docker组
            sudo usermod -aG docker $USER
            
            echo "✅ Docker安装完成"
            ;;
            
        *"CentOS"*|*"Red Hat"*|*"Rocky"*|*"AlmaLinux"*)
            echo "📦 在CentOS/RHEL系统上安装Docker..."
            # 安装yum-utils
            sudo yum install -y yum-utils
            
            # 添加Docker仓库
            sudo yum-config-manager \
                --add-repo \
                https://download.docker.com/linux/centos/docker-ce.repo
            
            # 安装Docker Engine
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            
            # 启动Docker服务
            sudo systemctl start docker
            sudo systemctl enable docker
            
            # 将当前用户添加到docker组
            sudo usermod -aG docker $USER
            
            echo "✅ Docker安装完成"
            ;;
            
        *"macOS"*)
            echo "📦 在macOS系统上安装Docker..."
            # 检查是否安装了Homebrew
            if ! command -v brew &> /dev/null; then
                echo "🍺 安装Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            # 使用Homebrew安装Docker Desktop
            brew install --cask docker
            
            echo "✅ Docker Desktop安装完成"
            echo "⚠️  请手动启动Docker Desktop应用程序，然后重新运行此脚本"
            exit 0
            ;;
            
        *)
            echo "❌ 不支持的操作系统: $OS"
            echo "请手动安装Docker和Docker Compose:"
            echo "   Docker: https://docs.docker.com/get-docker/"
            echo "   Docker Compose: https://docs.docker.com/compose/install/"
            exit 1
            ;;
    esac
}

# 安装Docker Compose的函数（针对旧版本Docker）
install_docker_compose() {
    echo "🔧 安装Docker Compose..."
    
    # 获取最新版本号
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    # 下载并安装Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # 添加执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建符号链接（如果需要）
    if [ ! -f /usr/bin/docker-compose ]; then
        sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
    fi
    
    echo "✅ Docker Compose安装完成"
}

# 检测操作系统
detect_os

# 检查Docker是否安装，如果没有则尝试安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    read -p "🔧 是否要自动安装Docker? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_docker
        echo "⚠️  Docker安装完成，请重新登录或运行 'newgrp docker' 以刷新用户组权限"
        echo "然后重新运行此脚本"
        exit 0
    else
        echo "请手动安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
else
    echo "✅ Docker已安装"
fi

# 检查Docker Compose是否安装（检查新版本的docker compose命令）
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    
    # 检查Docker版本是否支持compose插件
    DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    MAJOR_VERSION=$(echo $DOCKER_VERSION | cut -d. -f1)
    MINOR_VERSION=$(echo $DOCKER_VERSION | cut -d. -f2)
    
    if [[ $MAJOR_VERSION -gt 20 ]] || [[ $MAJOR_VERSION -eq 20 && $MINOR_VERSION -ge 10 ]]; then
        echo "⚠️  您的Docker版本支持compose插件，但似乎未安装"
        echo "请尝试: sudo apt-get install docker-compose-plugin (Ubuntu/Debian)"
        echo "或者: sudo yum install docker-compose-plugin (CentOS/RHEL)"
    else
        read -p "🔧 是否要自动安装Docker Compose? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker_compose
        else
            echo "请手动安装Docker Compose: https://docs.docker.com/compose/install/"
            exit 1
        fi
    fi
else
    echo "✅ Docker Compose已安装"
fi

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p data log data/svn conf

# 初始化环境配置
echo "🔧 初始化环境配置..."
if [ ! -f "conf/.env" ]; then
    if [ -f "conf/.env.dist" ]; then
        echo "📋 从模板创建.env文件..."
        cp conf/.env.dist conf/.env
        echo "✅ 已创建conf/.env文件"
    else
        echo "⚠️  未找到.env.dist模板，将在容器内自动创建"
    fi
else
    echo "✅ .env文件已存在"
fi

# 显示配置提示
if [ -f "conf/.env" ]; then
    echo ""
    echo "📝 重要提示:"
    echo "   请编辑 conf/.env 文件，配置你的API密钥"
    echo "   主要配置项："
    echo "   - LLM_PROVIDER: 选择AI服务商 (deepseek推荐)"
    echo "   - DEEPSEEK_API_KEY: DeepSeek API密钥"
    echo "   - GITLAB_ACCESS_TOKEN: GitLab访问令牌(可选)"
    echo ""
    
    # 检查是否需要用户配置
    if grep -q "DEEPSEEK_API_KEY=$" conf/.env || grep -q "DEEPSEEK_API_KEY=xxxx" conf/.env; then
        echo "⚠️  检测到API密钥未配置，请先配置后再启动："
        echo "   1. 编辑文件: vi conf/.env"
        echo "   2. 设置API密钥: DEEPSEEK_API_KEY=your_api_key_here"
        echo "   3. 然后运行: $0 --start"
        echo ""
        
        if [ "$1" != "--start" ] && [ "$1" != "--force" ]; then
            echo "💡 如果你已经配置完成，使用 --start 参数启动服务"
            exit 0
        fi
    fi
fi

# 检查docker-compose.yml文件
echo "🔍 检查docker-compose.yml文件..."
if [ ! -f "docker-compose.yml" ]; then
    echo "⚠️  未找到docker-compose.yml文件"
    echo "📥 正在从GitHub下载..."
    
    # 检查curl是否可用
    if command -v curl &> /dev/null; then
        if curl -L -o docker-compose.yml https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main/docker-compose.yml; then
            echo "✅ docker-compose.yml下载成功"
        else
            echo "❌ 使用curl下载失败，尝试wget..."
            if command -v wget &> /dev/null; then
                if wget -O docker-compose.yml https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main/docker-compose.yml; then
                    echo "✅ docker-compose.yml下载成功"
                else
                    echo "❌ 下载失败，请检查网络连接或手动下载"
                    echo "📝 手动下载地址: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB"
                    exit 1
                fi
            else
                echo "❌ curl和wget都不可用，请手动下载："
                echo "   1. 访问: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB"
                echo "   2. 下载docker-compose.yml文件到当前目录"
                echo "   3. 然后重新运行此脚本"
                exit 1
            fi
        fi
    elif command -v wget &> /dev/null; then
        if wget -O docker-compose.yml https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main/docker-compose.yml; then
            echo "✅ docker-compose.yml下载成功"
        else
            echo "❌ 下载失败，请检查网络连接或手动下载"
            echo "📝 手动下载地址: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB"
            exit 1
        fi
    else
        echo "❌ curl和wget都不可用，请手动下载："
        echo "   1. 访问: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB"
        echo "   2. 下载docker-compose.yml文件到当前目录"
        echo "   3. 然后重新运行此脚本"
        exit 1
    fi
else
    echo "✅ docker-compose.yml文件已存在"
fi

# 启动服务
echo "🐳 启动Docker服务..."

# 优先使用新版本的 docker compose 命令
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ 找不到可用的Docker Compose命令"
    exit 1
fi

echo "使用命令: $COMPOSE_CMD"
$COMPOSE_CMD up -d

echo ""
echo "✅ 服务启动完成！"
echo ""
echo "🌐 访问地址:"
echo "   - API服务: http://localhost:5001"
echo "   - 仪表板: http://localhost:5002"
echo ""
echo "📊 查看服务状态:"
echo "   $COMPOSE_CMD ps"
echo ""
echo "📝 查看日志:"
echo "   $COMPOSE_CMD logs -f"
echo ""
echo "🛑 停止服务:"
echo "   $COMPOSE_CMD down"
