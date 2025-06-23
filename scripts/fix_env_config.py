#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速配置修复脚本
解决当前环境配置中的关键问题
"""

import os
import shutil
from datetime import datetime

def backup_env_file(env_path: str) -> str:
    """备份环境配置文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{env_path}.backup_{timestamp}"
    shutil.copy2(env_path, backup_path)
    return backup_path

def fix_security_issues(env_path: str):
    """修复安全问题"""
    print("🔒 修复安全配置...")
    
    # 读取文件
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修改默认密码
    if 'DASHBOARD_USER=admin' in content and 'DASHBOARD_PASSWORD=admin' in content:
        print("  • 修改Dashboard默认密码")
        content = content.replace('DASHBOARD_PASSWORD=admin', 'DASHBOARD_PASSWORD=admin123')
        
        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    
    return False

def add_missing_configs(env_path: str):
    """添加缺失的关键配置"""
    print("📝 添加缺失的配置项...")
    
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 检查并添加DeepSeek API密钥（即使为空也要有这个配置项）
    has_deepseek_key = any('DEEPSEEK_API_KEY=' in line for line in lines)
    
    if not has_deepseek_key:
        print("  • 添加DeepSeek API密钥配置项")
        # 找到DeepSeek配置区域
        for i, line in enumerate(lines):
            if 'DEEPSEEK_API_BASE_URL=' in line:
                lines.insert(i, 'DEEPSEEK_API_KEY=\n')
                break
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return True
    
    return False

def optimize_current_config(env_path: str):
    """优化当前配置"""
    print("⚙️ 优化当前配置...")
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes = []
    
    # 确保日志级别合适
    if 'LOG_LEVEL=DEBUG' in content:
        content = content.replace('LOG_LEVEL=DEBUG', 'LOG_LEVEL=INFO')
        changes.append("日志级别调整为INFO")
    
    # 优化SVN检查频率（如果太频繁）
    if 'SVN_CHECK_CRONTAB=* * * * *' in content:
        content = content.replace('SVN_CHECK_CRONTAB=* * * * *', 'SVN_CHECK_CRONTAB=*/30 * * * *')
        changes.append("SVN检查频率调整为30分钟")
    
    if changes:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        for change in changes:
            print(f"  • {change}")
        
        return True
    
    return False

def generate_config_summary(env_path: str):
    """生成配置摘要"""
    print("\n📊 当前配置摘要:")
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取关键配置
    configs = {}
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            configs[key.strip()] = value.strip()
    
    # 显示关键配置
    key_configs = [
        ('LLM_PROVIDER', 'LLM提供商'),
        ('OLLAMA_API_BASE_URL', 'Ollama地址'),
        ('OLLAMA_API_MODEL', 'Ollama模型'),
        ('SVN_CHECK_ENABLED', 'SVN审查'),
        ('DASHBOARD_USER', 'Dashboard用户'),
        ('DASHBOARD_PASSWORD', 'Dashboard密码'),
        ('QUEUE_DRIVER', '队列驱动'),
        ('LOG_LEVEL', '日志级别')
    ]
    
    for key, desc in key_configs:
        value = configs.get(key, '未配置')
        if key == 'DASHBOARD_PASSWORD' and value:
            value = '*' * len(value)  # 隐藏密码
        print(f"  • {desc}: {value}")

def main():
    """主函数"""
    print("=== AI-Codereview-Gitlab 配置快速修复 ===\n")
    
    # 设置项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, 'conf', '.env')
    
    if not os.path.exists(env_path):
        print(f"❌ 配置文件不存在: {env_path}")
        return
    
    print(f"📁 配置文件: {env_path}")
    
    # 备份配置文件
    backup_path = backup_env_file(env_path)
    print(f"💾 配置文件已备份至: {backup_path}")
    
    # 执行修复
    changes_made = False
    
    # 修复安全问题
    if fix_security_issues(env_path):
        changes_made = True
    
    # 添加缺失配置
    if add_missing_configs(env_path):
        changes_made = True
    
    # 优化配置
    if optimize_current_config(env_path):
        changes_made = True
    
    if changes_made:
        print("\n✅ 配置修复完成！")
    else:
        print("\n✅ 配置检查完成，未发现需要修复的问题！")
    
    # 生成配置摘要
    generate_config_summary(env_path)
    
    print("\n📋 接下来您可以:")
    print("1. 根据需要在Web界面中进一步调整配置")
    print("2. 如果使用私有Git仓库，配置相应的访问令牌")
    print("3. 如果需要其他LLM提供商，配置相应的API密钥")
    print("4. 重启Web界面以应用配置变更")
    
    # 检查Ollama连接
    ollama_url = None
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('OLLAMA_API_BASE_URL='):
                ollama_url = line.split('=', 1)[1].strip()
                break
    
    if ollama_url:
        print(f"\n🔗 当前Ollama地址: {ollama_url}")
        print("   请确保Ollama服务正在运行并可访问")

if __name__ == "__main__":
    main()
