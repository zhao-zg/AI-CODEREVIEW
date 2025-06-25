#!/bin/bash
# Bash syntax checker for start.sh

echo "正在检查 start.sh 脚本语法..."

# Check if we have bash
if command -v bash >/dev/null 2>&1; then
    echo "使用 bash 检查语法..."
    bash -n start.sh
    if [ $? -eq 0 ]; then
        echo "✅ start.sh 语法检查通过"
    else
        echo "❌ start.sh 语法检查失败"
        exit 1
    fi
else
    echo "⚠️  bash 不可用，跳过语法检查"
fi

# Check for common issues
echo "检查常见问题..."

# Check for unmatched braces
echo "检查括号匹配..."
if [ $(grep -c '{' start.sh) -ne $(grep -c '}' start.sh) ]; then
    echo "❌ 大括号不匹配"
    echo "{ 数量: $(grep -c '{' start.sh)"
    echo "} 数量: $(grep -c '}' start.sh)"
    exit 1
else
    echo "✅ 大括号匹配"
fi

# Check for unmatched parentheses in function definitions
echo "检查函数定义..."
func_count=$(grep -c '()' start.sh)
echo "发现 $func_count 个函数定义"

echo "✅ 基本检查完成"
