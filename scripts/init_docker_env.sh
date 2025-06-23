#!/bin/bash
# Docker Compose 部署前的环境初始化脚本
# 自动创建完整的 .env 配置，解决配置不完整的问题

set -e

echo "🚀 AI-CodeReview-GitLab Docker Compose 部署前置脚本"
echo "=" * 60
echo "📋 解决 docker-compose 部署时 .env 数据不完整的问题"
echo "=" * 60

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ 未找到 Python 解释器，请安装 Python 3"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "✅ 找到 Python 解释器: $PYTHON_CMD"

# 运行环境初始化脚本
echo "🔧 运行环境配置初始化..."
$PYTHON_CMD scripts/init_env.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 环境初始化完成！现在可以启动 Docker Compose 服务"
    echo ""
    echo "📋 启动命令:"
    echo "   # 使用 Docker Hub 镜像 (推荐)"
    echo "   docker-compose -f docker-compose.dockerhub.yml up -d"
    echo ""
    echo "   # 或使用 GitHub Container Registry 镜像"
    echo "   docker-compose up -d"
    echo ""
    echo "   # 或本地构建"
    echo "   docker-compose up --build -d"
    echo ""
    echo "📖 访问服务:"
    echo "   - API 服务: http://localhost:5001"
    echo "   - Web 界面: http://localhost:5002"
    echo "   - 默认登录: admin / admin123"
    echo ""
else
    echo "❌ 环境初始化失败，请检查错误信息"
    exit 1
fi
