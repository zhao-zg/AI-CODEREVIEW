#!/bin/bash

# AI-CodeReview 项目清理脚本
# 用于清理临时文件、缓存文件和备份文件

set -e

echo "🧹 开始清理 AI-CodeReview 项目..."

# 清理 Python 缓存文件
echo "清理 Python 缓存文件..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.pyd" -delete 2>/dev/null || true

# 清理测试缓存
echo "清理测试缓存..."
rm -rf .pytest_cache/ 2>/dev/null || true
rm -rf .tox/ 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true
rm -f .coverage 2>/dev/null || true

# 清理编辑器临时文件
echo "清理编辑器临时文件..."
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true

# 清理备份文件
echo "清理备份文件..."
find . -name "*-old.*" -delete 2>/dev/null || true
find . -name "*-new.*" -delete 2>/dev/null || true
find . -name "*-backup.*" -delete 2>/dev/null || true
find . -name "*_backup.*" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true

# 清理临时文件
echo "清理临时文件..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "*_temp.*" -delete 2>/dev/null || true

# 清理系统文件
echo "清理系统文件..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true
find . -name "Desktop.ini" -delete 2>/dev/null || true

# 清理日志文件（保留目录结构）
echo "清理日志文件..."
find ./log -name "*.log" -delete 2>/dev/null || true

# 清理 Node.js 相关（如果存在）
echo "清理 Node.js 文件..."
rm -rf node_modules/ 2>/dev/null || true
rm -f npm-debug.log* 2>/dev/null || true
rm -f yarn-debug.log* 2>/dev/null || true
rm -f yarn-error.log* 2>/dev/null || true

# 清理构建产物
echo "清理构建产物..."
rm -rf build/ 2>/dev/null || true
rm -rf dist/ 2>/dev/null || true
rm -rf *.egg-info/ 2>/dev/null || true

# 显示清理结果
echo ""
echo "✅ 项目清理完成！"
echo ""
echo "📊 当前项目结构："
echo "├── 核心文件"
echo "│   ├── api.py, ui.py (主应用)"
echo "│   ├── docker-compose*.yml (容器配置)"
echo "│   ├── Dockerfile (镜像构建)"
echo "│   └── requirements.txt (依赖)"
echo "├── 配置目录"
echo "│   ├── conf/ (配置文件)"
echo "│   ├── scripts/ (脚本文件)"
echo "│   └── docs/ (文档)"
echo "├── 启动脚本"
echo "│   ├── start.sh / start.bat (主启动脚本)"
echo "│   └── run_ui.sh / run_ui.bat (UI启动脚本)"
echo "└── 测试文件"
echo "    ├── test_multi_container.py"
echo "    └── test_single_container.py"
echo ""
echo "🚀 项目已准备就绪，可以使用 ./start.sh 或 start.bat 启动！"
