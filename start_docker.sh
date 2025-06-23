#!/bin/bash
# Docker部署启动脚本
# 自动初始化环境配置并启动服务

set -e

echo "🚀 AI代码审查系统 - Docker部署脚本"
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
