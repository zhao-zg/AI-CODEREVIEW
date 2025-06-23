#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置检查脚本
检查 .env 文件中的配置项是否完整，并提供配置建议
"""

import os
import sys
import json
import re
from typing import Dict, List, Any, Optional

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

def check_llm_config(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """检查LLM配置"""
    issues = []
    
    llm_provider = env_vars.get('LLM_PROVIDER', '')
    
    if not llm_provider:
        issues.append({
            'type': 'missing',
            'category': 'LLM配置',
            'key': 'LLM_PROVIDER',
            'message': '未配置LLM提供商',
            'suggestion': '请设置为以下之一: deepseek, openai, zhipuai, qwen, ollama'
        })
        return issues
    
    # 检查对应提供商的配置
    if llm_provider == 'deepseek':
        api_key = env_vars.get('DEEPSEEK_API_KEY', '')
        if not api_key:
            issues.append({
                'type': 'missing',
                'category': 'DeepSeek配置',
                'key': 'DEEPSEEK_API_KEY',
                'message': 'DeepSeek API密钥未配置',
                'suggestion': '请在DeepSeek官网获取API密钥'
            })
    elif llm_provider == 'openai':
        api_key = env_vars.get('OPENAI_API_KEY', '')
        if not api_key or api_key == 'xxxx':
            issues.append({
                'type': 'incomplete',
                'category': 'OpenAI配置',
                'key': 'OPENAI_API_KEY',
                'message': 'OpenAI API密钥使用示例值',
                'suggestion': '请配置真实的OpenAI API密钥'
            })
    elif llm_provider == 'zhipuai':
        api_key = env_vars.get('ZHIPUAI_API_KEY', '')
        if not api_key or api_key == 'xxxx':
            issues.append({
                'type': 'incomplete',
                'category': '智谱AI配置',
                'key': 'ZHIPUAI_API_KEY',
                'message': '智谱AI API密钥使用示例值',
                'suggestion': '请配置真实的智谱AI API密钥'
            })
    elif llm_provider == 'qwen':
        api_key = env_vars.get('QWEN_API_KEY', '')
        if not api_key or api_key.startswith('sk-xxx'):
            issues.append({
                'type': 'incomplete',
                'category': '通义千问配置',
                'key': 'QWEN_API_KEY',
                'message': '通义千问API密钥使用示例值',
                'suggestion': '请配置真实的通义千问API密钥'
            })
    elif llm_provider == 'ollama':
        base_url = env_vars.get('OLLAMA_API_BASE_URL', '')
        if not base_url:
            issues.append({
                'type': 'missing',
                'category': 'Ollama配置',
                'key': 'OLLAMA_API_BASE_URL',
                'message': 'Ollama API地址未配置',
                'suggestion': '请配置Ollama服务地址，如: http://localhost:11434'
            })
        model = env_vars.get('OLLAMA_API_MODEL', '')
        if not model:
            issues.append({
                'type': 'missing',
                'category': 'Ollama配置',
                'key': 'OLLAMA_API_MODEL',
                'message': 'Ollama模型未配置',
                'suggestion': '请配置要使用的Ollama模型名称'
            })
    
    return issues

def check_git_config(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """检查Git配置"""
    issues = []
    
    gitlab_token = env_vars.get('GITLAB_ACCESS_TOKEN', '')
    github_token = env_vars.get('GITHUB_ACCESS_TOKEN', '')
    gitlab_url = env_vars.get('GITLAB_URL', '')
    
    if not gitlab_token and not github_token:
        issues.append({
            'type': 'warning',
            'category': 'Git配置',
            'key': 'GITLAB_ACCESS_TOKEN / GITHUB_ACCESS_TOKEN',
            'message': '未配置GitLab或GitHub访问令牌',
            'suggestion': '如果需要访问私有仓库，请配置相应的访问令牌'
        })
    
    if gitlab_token and not gitlab_url:
        issues.append({
            'type': 'warning',
            'category': 'GitLab配置',
            'key': 'GITLAB_URL',
            'message': '配置了GitLab令牌但未配置GitLab URL',
            'suggestion': '请配置GitLab服务器地址，如: https://gitlab.example.com'
        })
    
    return issues

def check_queue_config(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """检查队列配置"""
    issues = []
    
    queue_driver = env_vars.get('QUEUE_DRIVER', 'async')
    
    if queue_driver == 'rq':
        redis_host = env_vars.get('REDIS_HOST', '')
        redis_port = env_vars.get('REDIS_PORT', '')
        
        if not redis_host:
            issues.append({
                'type': 'missing',
                'category': 'Redis配置',
                'key': 'REDIS_HOST',
                'message': '使用RQ队列但未配置Redis主机',
                'suggestion': '请配置Redis服务器地址，如: localhost 或 redis'
            })
        
        if not redis_port:
            issues.append({
                'type': 'missing',
                'category': 'Redis配置',
                'key': 'REDIS_PORT',
                'message': '使用RQ队列但未配置Redis端口',
                'suggestion': '请配置Redis端口，通常为: 6379'
            })
    
    return issues

def check_svn_config(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """检查SVN配置"""
    issues = []
    
    svn_enabled = env_vars.get('SVN_CHECK_ENABLED', '0')
    
    if svn_enabled == '1':
        svn_repos = env_vars.get('SVN_REPOSITORIES', '')
        
        if not svn_repos:
            issues.append({
                'type': 'missing',
                'category': 'SVN配置',
                'key': 'SVN_REPOSITORIES',
                'message': '启用了SVN但未配置SVN仓库',
                'suggestion': '请配置SVN仓库信息'
            })
        else:
            try:
                repos = json.loads(svn_repos)
                for i, repo in enumerate(repos):
                    if 'remote_url' not in repo or not repo['remote_url']:
                        issues.append({
                            'type': 'incomplete',
                            'category': 'SVN配置',
                            'key': f'SVN_REPOSITORIES[{i}].remote_url',
                            'message': f'SVN仓库 {i+1} 缺少远程URL',
                            'suggestion': '请配置SVN仓库的远程URL'
                        })
                    
                    if 'username' not in repo or not repo['username']:
                        issues.append({
                            'type': 'incomplete',
                            'category': 'SVN配置',
                            'key': f'SVN_REPOSITORIES[{i}].username',
                            'message': f'SVN仓库 {i+1} 缺少用户名',
                            'suggestion': '请配置SVN仓库的用户名'
                        })
                    
                    if 'password' not in repo or not repo['password']:
                        issues.append({
                            'type': 'incomplete',
                            'category': 'SVN配置',
                            'key': f'SVN_REPOSITORIES[{i}].password',
                            'message': f'SVN仓库 {i+1} 缺少密码',
                            'suggestion': '请配置SVN仓库的密码'
                        })
            except json.JSONDecodeError:
                issues.append({
                    'type': 'error',
                    'category': 'SVN配置',
                    'key': 'SVN_REPOSITORIES',
                    'message': 'SVN仓库配置格式错误',
                    'suggestion': '请检查SVN_REPOSITORIES配置是否为有效的JSON格式'
                })
    
    return issues

def check_notification_config(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """检查通知配置"""
    issues = []
    
    notification_configs = [
        ('DINGTALK_ENABLED', 'DINGTALK_WEBHOOK_URL', '钉钉'),
        ('WECOM_ENABLED', 'WECOM_WEBHOOK_URL', '企业微信'),
        ('FEISHU_ENABLED', 'FEISHU_WEBHOOK_URL', '飞书'),
        ('EXTRA_WEBHOOK_ENABLED', 'EXTRA_WEBHOOK_URL', '自定义Webhook')
    ]
    
    for enabled_key, url_key, name in notification_configs:
        enabled = env_vars.get(enabled_key, '0')
        if enabled == '1':
            webhook_url = env_vars.get(url_key, '')
            if not webhook_url or webhook_url.endswith('xxx'):
                issues.append({
                    'type': 'incomplete',
                    'category': '通知配置',
                    'key': url_key,
                    'message': f'启用了{name}通知但未配置Webhook URL',
                    'suggestion': f'请配置{name}的Webhook URL'
                })
    
    return issues

def check_dashboard_config(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """检查Dashboard配置"""
    issues = []
    
    dashboard_user = env_vars.get('DASHBOARD_USER', '')
    dashboard_password = env_vars.get('DASHBOARD_PASSWORD', '')
    
    if dashboard_user == 'admin' and dashboard_password == 'admin':
        issues.append({
            'type': 'security',
            'category': 'Dashboard配置',
            'key': 'DASHBOARD_USER / DASHBOARD_PASSWORD',
            'message': '使用默认的Dashboard用户名和密码',
            'suggestion': '为了安全起见，请修改默认的用户名和密码'
        })
    
    return issues

def check_required_config(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """检查必需的配置项"""
    issues = []
    
    required_configs = [
        ('SERVER_PORT', '服务端口'),
        ('LLM_PROVIDER', 'LLM提供商'),
        ('SUPPORTED_EXTENSIONS', '支持的文件扩展名'),
        ('REVIEW_MAX_TOKENS', '审查最大Token数'),
        ('REVIEW_STYLE', '审查风格')
    ]
    
    for key, description in required_configs:
        if key not in env_vars or not env_vars[key]:
            issues.append({
                'type': 'missing',
                'category': '基础配置',
                'key': key,
                'message': f'缺少必需的配置项: {description}',
                'suggestion': f'请配置 {key}'
            })
    
    return issues

def main():
    """主函数"""
    print("=== AI-Codereview-Gitlab 环境配置检查 ===\n")
    
    # 设置项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, 'conf', '.env')
    env_dist_path = os.path.join(project_root, 'conf', '.env.dist')
    
    print(f"检查配置文件: {env_path}")
    
    if not os.path.exists(env_path):
        print(f"❌ 配置文件不存在: {env_path}")
        if os.path.exists(env_dist_path):
            print(f"💡 发现模板文件: {env_dist_path}")
            print("   建议复制模板文件为 .env 并进行配置")
        return
    
    # 加载环境变量
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        print("❌ 配置文件为空或格式错误")
        return
    
    print(f"✅ 成功加载 {len(env_vars)} 个配置项\n")
    
    # 执行各项检查
    all_issues = []
    
    print("🔍 开始检查配置项...")
    
    # 基础配置检查
    issues = check_required_config(env_vars)
    all_issues.extend(issues)
    
    # LLM配置检查
    issues = check_llm_config(env_vars)
    all_issues.extend(issues)
    
    # Git配置检查
    issues = check_git_config(env_vars)
    all_issues.extend(issues)
    
    # 队列配置检查
    issues = check_queue_config(env_vars)
    all_issues.extend(issues)
    
    # SVN配置检查
    issues = check_svn_config(env_vars)
    all_issues.extend(issues)
    
    # 通知配置检查
    issues = check_notification_config(env_vars)
    all_issues.extend(issues)
    
    # Dashboard配置检查
    issues = check_dashboard_config(env_vars)
    all_issues.extend(issues)
    
    # 输出结果
    print("\n=== 检查结果 ===")
    
    if not all_issues:
        print("✅ 所有配置项检查通过，未发现问题")
        return
    
    # 按类型分组显示
    issues_by_type = {}
    for issue in all_issues:
        issue_type = issue['type']
        if issue_type not in issues_by_type:
            issues_by_type[issue_type] = []
        issues_by_type[issue_type].append(issue)
    
    type_icons = {
        'missing': '❌',
        'incomplete': '⚠️',
        'error': '💥',
        'warning': '⚡',
        'security': '🔒'
    }
    
    type_names = {
        'missing': '缺失配置',
        'incomplete': '不完整配置',
        'error': '配置错误',
        'warning': '配置警告',
        'security': '安全建议'
    }
    
    for issue_type, issues in issues_by_type.items():
        icon = type_icons.get(issue_type, '❓')
        name = type_names.get(issue_type, issue_type)
        
        print(f"\n{icon} {name} ({len(issues)} 项):")
        
        for issue in issues:
            print(f"  • [{issue['category']}] {issue['message']}")
            print(f"    配置项: {issue['key']}")
            print(f"    建议: {issue['suggestion']}")
            print()
    
    print(f"📊 总共发现 {len(all_issues)} 个配置问题")
    
    # 提供解决建议
    print("\n=== 解决建议 ===")
    print("1. 可以通过Web界面的配置管理功能来修改配置")
    print("2. 也可以直接编辑 conf/.env 文件")
    print("3. 参考 conf/.env.dist 文件中的示例配置")
    print("4. 重新启动应用以使配置生效")

if __name__ == "__main__":
    main()
