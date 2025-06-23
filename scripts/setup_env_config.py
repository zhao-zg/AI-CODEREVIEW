#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置完善脚本
自动检查并完善 .env 配置文件中缺失的配置项
"""

import os
import sys
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any

def load_env_file(env_path: str) -> Dict[str, str]:
    """加载环境变量文件"""
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def backup_env_file(env_path: str) -> str:
    """备份环境配置文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{env_path}.backup_{timestamp}"
    shutil.copy2(env_path, backup_path)
    return backup_path

def get_missing_configs(current_env: Dict[str, str], template_env: Dict[str, str]) -> Dict[str, str]:
    """获取缺失的配置项"""
    missing = {}
    
    for key, value in template_env.items():
        if key not in current_env:
            missing[key] = value
    
    return missing

def interactive_config_setup():
    """交互式配置设置"""
    print("\n🛠️  开始交互式配置...")
    
    configs = {}
    
    # LLM配置
    print("\n=== 大语言模型配置 ===")
    llm_provider = input("请选择LLM提供商 (deepseek/openai/zhipuai/qwen/ollama) [ollama]: ").strip().lower()
    if not llm_provider:
        llm_provider = "ollama"
    configs['LLM_PROVIDER'] = llm_provider
    
    # 根据选择的提供商配置相应的API密钥
    if llm_provider == 'deepseek':
        api_key = input("请输入DeepSeek API密钥 (留空跳过): ").strip()
        if api_key:
            configs['DEEPSEEK_API_KEY'] = api_key
    elif llm_provider == 'openai':
        api_key = input("请输入OpenAI API密钥 (留空跳过): ").strip()
        if api_key:
            configs['OPENAI_API_KEY'] = api_key
    elif llm_provider == 'zhipuai':
        api_key = input("请输入智谱AI API密钥 (留空跳过): ").strip()
        if api_key:
            configs['ZHIPUAI_API_KEY'] = api_key
    elif llm_provider == 'qwen':
        api_key = input("请输入通义千问API密钥 (留空跳过): ").strip()
        if api_key:
            configs['QWEN_API_KEY'] = api_key
    elif llm_provider == 'ollama':
        ollama_url = input("请输入Ollama API地址 [http://localhost:11434]: ").strip()
        if not ollama_url:
            ollama_url = "http://localhost:11434"
        configs['OLLAMA_API_BASE_URL'] = ollama_url
        
        ollama_model = input("请输入Ollama模型名称 [qwen2.5:1.5b]: ").strip()
        if not ollama_model:
            ollama_model = "qwen2.5:1.5b"
        configs['OLLAMA_API_MODEL'] = ollama_model
    
    # Git配置
    print("\n=== Git仓库配置 ===")
    setup_git = input("是否需要配置GitLab/GitHub访问令牌？(y/n) [n]: ").strip().lower()
    if setup_git == 'y':
        gitlab_token = input("请输入GitLab访问令牌 (留空跳过): ").strip()
        if gitlab_token:
            configs['GITLAB_ACCESS_TOKEN'] = gitlab_token
            gitlab_url = input("请输入GitLab服务器地址 (如: https://gitlab.example.com): ").strip()
            if gitlab_url:
                configs['GITLAB_URL'] = gitlab_url
        
        github_token = input("请输入GitHub访问令牌 (留空跳过): ").strip()
        if github_token:
            configs['GITHUB_ACCESS_TOKEN'] = github_token
    
    # Dashboard安全配置
    print("\n=== Dashboard安全配置 ===")
    change_dashboard = input("是否修改默认的Dashboard用户名和密码？(y/n) [y]: ").strip().lower()
    if change_dashboard != 'n':
        dashboard_user = input("请输入Dashboard用户名 [admin]: ").strip()
        if not dashboard_user:
            dashboard_user = "admin"
        configs['DASHBOARD_USER'] = dashboard_user
        
        dashboard_password = input("请输入Dashboard密码 [admin123]: ").strip()
        if not dashboard_password:
            dashboard_password = "admin123"
        configs['DASHBOARD_PASSWORD'] = dashboard_password
    
    # 队列配置
    print("\n=== 队列配置 ===")
    queue_driver = input("请选择队列驱动 (async/rq) [async]: ").strip().lower()
    if not queue_driver:
        queue_driver = "async"
    configs['QUEUE_DRIVER'] = queue_driver
    
    if queue_driver == 'rq':
        redis_host = input("请输入Redis主机地址 [localhost]: ").strip()
        if not redis_host:
            redis_host = "localhost"
        configs['REDIS_HOST'] = redis_host
        
        redis_port = input("请输入Redis端口 [6379]: ").strip()
        if not redis_port:
            redis_port = "6379"
        configs['REDIS_PORT'] = redis_port
    
    # SVN配置
    print("\n=== SVN配置 ===")
    setup_svn = input("是否需要配置SVN代码审查？(y/n) [n]: ").strip().lower()
    if setup_svn == 'y':
        configs['SVN_CHECK_ENABLED'] = '1'
        
        svn_repos = []
        while True:
            print(f"\n配置SVN仓库 #{len(svn_repos) + 1}:")
            repo_name = input("请输入仓库名称: ").strip()
            if not repo_name:
                break
            
            remote_url = input("请输入SVN远程URL: ").strip()
            if not remote_url:
                break
            
            username = input("请输入SVN用户名: ").strip()
            password = input("请输入SVN密码: ").strip()
            
            local_path = f"data/svn/{repo_name}"
            check_hours = input("请输入检查间隔(小时) [1]: ").strip()
            if not check_hours:
                check_hours = "1"
            
            repo_config = {
                "name": repo_name,
                "remote_url": remote_url,
                "local_path": local_path,
                "username": username,
                "password": password,
                "check_hours": int(check_hours)
            }
            svn_repos.append(repo_config)
            
            more_repos = input("是否添加更多SVN仓库？(y/n) [n]: ").strip().lower()
            if more_repos != 'y':
                break
        
        if svn_repos:
            configs['SVN_REPOSITORIES'] = json.dumps(svn_repos, ensure_ascii=False)
    else:
        configs['SVN_CHECK_ENABLED'] = '0'
    
    # 通知配置
    print("\n=== 通知配置 ===")
    setup_notifications = input("是否需要配置消息通知？(y/n) [n]: ").strip().lower()
    if setup_notifications == 'y':
        # 钉钉
        dingtalk = input("是否启用钉钉通知？(y/n) [n]: ").strip().lower()
        if dingtalk == 'y':
            configs['DINGTALK_ENABLED'] = '1'
            webhook_url = input("请输入钉钉Webhook URL: ").strip()
            if webhook_url:
                configs['DINGTALK_WEBHOOK_URL'] = webhook_url
        
        # 企业微信
        wecom = input("是否启用企业微信通知？(y/n) [n]: ").strip().lower()
        if wecom == 'y':
            configs['WECOM_ENABLED'] = '1'
            webhook_url = input("请输入企业微信Webhook URL: ").strip()
            if webhook_url:
                configs['WECOM_WEBHOOK_URL'] = webhook_url
        
        # 飞书
        feishu = input("是否启用飞书通知？(y/n) [n]: ").strip().lower()
        if feishu == 'y':
            configs['FEISHU_ENABLED'] = '1'
            webhook_url = input("请输入飞书Webhook URL: ").strip()
            if webhook_url:
                configs['FEISHU_WEBHOOK_URL'] = webhook_url
    
    return configs

def update_env_file(env_path: str, updates: Dict[str, str]):
    """更新环境配置文件"""
    # 读取原始文件内容
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # 构建现有配置的映射
    existing_keys = set()
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key = line.split('=', 1)[0].strip()
            existing_keys.add(key)
            
            # 如果这个键需要更新，替换这一行
            if key in updates:
                lines[i] = f"{key}={updates[key]}\n"
                del updates[key]  # 从更新列表中移除，避免重复添加
    
    # 添加新的配置项
    if updates:
        lines.append("\n# === 自动添加的配置项 ===\n")
        for key, value in updates.items():
            lines.append(f"{key}={value}\n")
    
    # 写回文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def main():
    """主函数"""
    print("=== AI-Codereview-Gitlab 环境配置完善工具 ===\n")
    
    # 设置项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, 'conf', '.env')
    env_dist_path = os.path.join(project_root, 'conf', '.env.dist')
    
    print(f"项目目录: {project_root}")
    print(f"配置文件: {env_path}")
    print(f"模板文件: {env_dist_path}")
    
    # 检查模板文件是否存在
    if not os.path.exists(env_dist_path):
        print(f"❌ 模板文件不存在: {env_dist_path}")
        return
    
    # 如果配置文件不存在，从模板复制
    if not os.path.exists(env_path):
        print("📋 配置文件不存在，从模板创建...")
        shutil.copy2(env_dist_path, env_path)
        print(f"✅ 已创建配置文件: {env_path}")
    
    # 加载配置
    current_env = load_env_file(env_path)
    template_env = load_env_file(env_dist_path)
    
    print(f"📊 当前配置项: {len(current_env)} 个")
    print(f"📊 模板配置项: {len(template_env)} 个")
    
    # 检查缺失的配置
    missing_configs = get_missing_configs(current_env, template_env)
    
    if missing_configs:
        print(f"⚠️  发现 {len(missing_configs)} 个缺失的配置项:")
        for key in missing_configs.keys():
            print(f"  • {key}")
    else:
        print("✅ 所有模板配置项都已存在")
    
    # 询问用户是否进行交互式配置
    print("\n" + "="*50)
    setup_mode = input("请选择配置模式:\n1. 快速模式 (使用默认值补全缺失配置)\n2. 交互模式 (逐项配置)\n3. 仅显示当前问题 (不修改)\n请输入选择 (1/2/3) [3]: ").strip()
    
    if setup_mode == '1':
        # 快速模式 - 添加缺失的配置项
        if missing_configs:
            print("\n🚀 快速模式：补全缺失配置...")
            backup_path = backup_env_file(env_path)
            print(f"📄 已备份原配置文件到: {backup_path}")
            
            update_env_file(env_path, missing_configs)
            print(f"✅ 已补全 {len(missing_configs)} 个配置项")
            print("⚠️  请手动检查并修改相关配置值")
        else:
            print("✅ 无需补全配置")
    
    elif setup_mode == '2':
        # 交互模式
        print("\n🛠️  交互模式：个性化配置...")
        backup_path = backup_env_file(env_path)
        print(f"📄 已备份原配置文件到: {backup_path}")
        
        interactive_configs = interactive_config_setup()
        
        if interactive_configs:
            # 合并缺失的配置和交互配置
            all_updates = {**missing_configs, **interactive_configs}
            update_env_file(env_path, all_updates)
            print(f"\n✅ 配置完成！已更新 {len(all_updates)} 个配置项")
        else:
            print("\n⚠️  未进行任何配置更改")
    
    else:
        # 仅显示模式
        print("\n📋 当前配置问题总结:")
        
        # 重新运行检查脚本显示详细问题
        check_script = os.path.join(project_root, 'scripts', 'check_env_config.py')
        if os.path.exists(check_script):
            print("\n" + "="*50)
            os.system(f'python "{check_script}"')
        
        print("\n💡 如需修改配置，请:")
        print("1. 重新运行此脚本选择其他模式")
        print("2. 直接编辑 conf/.env 文件")
        print("3. 使用Web界面的配置管理功能")
    
    print("\n🎉 环境配置检查完成！")
    
    if setup_mode in ['1', '2']:
        restart_ui = input("\n是否重启Web界面以应用新配置？(y/n) [n]: ").strip().lower()
        if restart_ui == 'y':
            print("🔄 重启Web界面...")
            # 这里可以添加重启逻辑，或者给出重启指令
            print("请手动重启Web界面：streamlit run ui.py")

if __name__ == "__main__":
    main()
