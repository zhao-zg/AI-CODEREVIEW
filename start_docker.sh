#!/bin/bash
# Docker部署启动脚本
# 自动初始化环境配置并启动服务

set -e

echo "🚀 AI-CodeReview 代码审查系统 - Docker部署脚本"
echo "=================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
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
docker-compose up -d

echo ""
echo "✅ 服务启动完成！"
echo ""
echo "🌐 访问地址:"
echo "   - API服务: http://localhost:5001"
echo "   - 仪表板: http://localhost:5002"
echo ""
echo "📊 查看服务状态:"
echo "   docker-compose ps"
echo ""
echo "📝 查看日志:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 停止服务:"
echo "   docker-compose down"
