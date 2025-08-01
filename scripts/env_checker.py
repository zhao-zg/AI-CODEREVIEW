#!/usr/bin/env python3
"""
环境配置检查和初始化脚本
用于确保 .env 文件存在并包含 .env.dist 中的所有参数
"""

import os
import sys
import shutil
from pathlib import Path

def log_info(message):
    """打印信息日志"""
    print(f"[INFO] {message}")

def log_warning(message):
    """打印警告日志"""
    print(f"[WARNING] {message}")

def log_error(message):
    """打印错误日志"""
    print(f"[ERROR] {message}")

def read_env_file(file_path):
    """读取环境变量文件并解析参数"""
    if not os.path.exists(file_path):
        return {}
    
    env_vars = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue
                
                # 解析环境变量
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    env_vars[key] = value
                else:
                    log_warning(f"在 {file_path} 第 {line_number} 行发现无效格式: {line}")
        
        log_info(f"从 {file_path} 读取了 {len(env_vars)} 个环境变量")
        return env_vars
        
    except Exception as e:
        log_error(f"读取文件 {file_path} 失败: {e}")
        return {}

def write_env_file(file_path, env_vars, append_mode=False):
    """写入环境变量到文件"""
    try:
        mode = 'a' if append_mode else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            if append_mode:
                f.write('\n# ========================================\n')
                f.write('# 以下参数由环境检查脚本自动添加\n')
                f.write('# ========================================\n')
            
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        action = "追加" if append_mode else "写入"
        log_info(f"成功{action} {len(env_vars)} 个环境变量到 {file_path}")
        return True
        
    except Exception as e:
        log_error(f"写入文件 {file_path} 失败: {e}")
        return False

def get_env_file_content_with_comments(file_path):
    """获取包含注释的完整文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        log_error(f"读取文件 {file_path} 失败: {e}")
        return ""

def check_and_initialize_env():
    """检查并初始化环境配置"""
    log_info("开始环境配置检查...")
    
    # 定义文件路径
    env_dist_path = "conf_templates/.env.dist"
    env_path = "conf/.env"
    
    # 检查 .env.dist 是否存在
    if not os.path.exists(env_dist_path):
        log_error(f"配置模板文件 {env_dist_path} 不存在！")
        return False
    
    # 读取 .env.dist 中的所有参数
    log_info(f"读取配置模板: {env_dist_path}")
    dist_vars = read_env_file(env_dist_path)
    
    if not dist_vars:
        log_error(f"配置模板 {env_dist_path} 为空或格式错误！")
        return False
    
    log_info(f"配置模板包含 {len(dist_vars)} 个环境变量")
    
    # 检查 .env 文件是否存在
    if not os.path.exists(env_path):
        log_warning(f"环境配置文件 {env_path} 不存在")
        log_info(f"正在从 {env_dist_path} 复制配置...")
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(env_path), exist_ok=True)
            
            # 复制完整的 .env.dist 文件（包含注释）
            shutil.copy2(env_dist_path, env_path)
            log_info(f"✅ 成功创建 {env_path}")
            return True
            
        except Exception as e:
            log_error(f"复制配置文件失败: {e}")
            return False
    
    # .env 文件存在，检查是否包含所有必需的参数
    log_info(f"检查现有环境配置: {env_path}")
    current_vars = read_env_file(env_path)
    
    # 找出缺失的参数
    missing_vars = {}
    for key, value in dist_vars.items():
        if key not in current_vars:
            missing_vars[key] = value
    
    if not missing_vars:
        log_info("✅ 环境配置完整，所有必需参数都已存在")
        return True
    
    # 有缺失的参数，需要追加
    log_warning(f"发现 {len(missing_vars)} 个缺失的环境变量:")
    for key in missing_vars.keys():
        log_warning(f"  - {key}")
    
    log_info("正在补充缺失的环境变量...")
    
    # 追加缺失的参数到 .env 文件
    if write_env_file(env_path, missing_vars, append_mode=True):
        log_info("✅ 环境配置更新完成")
        return True
    else:
        log_error("❌ 环境配置更新失败")
        return False

def validate_critical_config():
    """验证关键配置项"""
    log_info("验证关键配置项...")
    
    env_path = "conf/.env"
    if not os.path.exists(env_path):
        log_error("环境配置文件不存在，无法验证")
        return False
    
    current_vars = read_env_file(env_path)
    
    # 定义关键配置项
    critical_configs = {
        'LLM_PROVIDER': '大模型供应商',
        'TZ': '时区设置'
    }
    
    missing_critical = []
    for key, description in critical_configs.items():
        if key not in current_vars or not current_vars[key]:
            missing_critical.append(f"{key} ({description})")
    
    if missing_critical:
        log_warning("以下关键配置项缺失或为空:")
        for item in missing_critical:
            log_warning(f"  - {item}")
        log_warning("请手动配置这些参数后再启动服务")
        return False
    
    log_info("✅ 关键配置项验证通过")
    return True

def show_config_summary():
    """显示配置摘要"""
    log_info("配置摘要:")
    
    env_path = "conf/.env"
    if not os.path.exists(env_path):
        log_error("环境配置文件不存在")
        return
    
    current_vars = read_env_file(env_path)
    
    # 显示主要配置
    key_configs = [
        'LLM_PROVIDER',
        'TZ',
        'VERSION_TRACKING_ENABLED',
        'LOG_LEVEL'
    ]
    
    print("\n" + "="*50)
    print("主要配置项:")
    for key in key_configs:
        value = current_vars.get(key, '未设置')
        print(f"  {key}: {value}")
    
    # 统计各类配置
    ai_providers = ['DEEPSEEK', 'OPENAI', 'ZHIPUAI', 'QWEN', 'JEDI', 'OLLAMA']
    configured_providers = []
    
    for provider in ai_providers:
        api_key = f"{provider}_API_KEY"
        if api_key in current_vars and current_vars[api_key]:
            configured_providers.append(provider.lower())
    
    print(f"\n已配置的AI模型: {', '.join(configured_providers) if configured_providers else '无'}")
    print(f"总配置项数量: {len(current_vars)}")
    print("="*50 + "\n")

def main():
    """主函数"""
    print("🚀 AI-CodeReview 环境配置检查器")
    print("="*60)
    
    try:
        # 检查并初始化环境配置
        if not check_and_initialize_env():
            log_error("环境配置检查失败！")
            return False
        
        # 验证关键配置项
        if not validate_critical_config():
            log_warning("关键配置项验证失败，但服务仍可启动")
        
        # 显示配置摘要
        show_config_summary()
        
        log_info("✅ 环境配置检查完成，可以启动服务")
        return True
        
    except Exception as e:
        log_error(f"环境配置检查过程中发生异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
