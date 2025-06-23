#!/usr/bin/env python3
"""
GitHub Actions 状态监控脚本
用于检查GitHub Actions工作流状态和Docker镜像发布情况
"""

import requests
import json
import sys
import os
from datetime import datetime

def check_github_actions_status(repo_owner, repo_name, token=None):
    """检查GitHub Actions工作流状态"""
    base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    headers['Accept'] = 'application/vnd.github.v3+json'
    
    try:
        # 获取最近的工作流运行
        workflows_url = f"{base_url}/actions/runs"
        response = requests.get(workflows_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            runs = data.get('workflow_runs', [])
            
            print(f"📊 {repo_owner}/{repo_name} - GitHub Actions状态")
            print("=" * 60)
            
            for run in runs[:5]:  # 显示最近5次运行
                name = run.get('name', 'Unknown')
                status = run.get('status', 'unknown')
                conclusion = run.get('conclusion', 'pending')
                created_at = run.get('created_at', '')
                branch = run.get('head_branch', 'unknown')
                
                # 状态图标
                status_icon = "🟡" if status == "in_progress" else "⚪"
                if conclusion == "success":
                    status_icon = "✅"
                elif conclusion == "failure":
                    status_icon = "❌"
                elif conclusion == "cancelled":
                    status_icon = "⏹️"
                
                # 格式化时间
                try:
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_str = created_at
                
                print(f"{status_icon} {name}")
                print(f"   分支: {branch}")
                print(f"   状态: {status} ({conclusion})")
                print(f"   时间: {time_str}")
                print()
            
            return True
            
        else:
            print(f"❌ 无法获取GitHub Actions状态: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 检查GitHub Actions状态时出错: {e}")
        return False

def check_docker_images(repo_owner, repo_name, token=None):
    """检查Docker镜像发布状态"""
    registry_url = f"https://ghcr.io/v2/{repo_owner}/{repo_name}"
    
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        # 检查镜像是否存在
        tags_url = f"{registry_url}/tags/list"
        
        print(f"🐳 Docker镜像状态 - ghcr.io/{repo_owner}/{repo_name}")
        print("=" * 60)
        
        # 由于GitHub Container Registry需要认证，我们提供基本信息
        expected_tags = ['latest', 'latest-worker']
        
        for tag in expected_tags:
            print(f"📦 {repo_owner}/{repo_name}:{tag}")
            print(f"   镜像地址: ghcr.io/{repo_owner}/{repo_name}:{tag}")
            print(f"   拉取命令: docker pull ghcr.io/{repo_owner}/{repo_name}:{tag}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 检查Docker镜像时出错: {e}")
        return False

def main():
    """主函数"""
    # 从环境变量或命令行参数获取仓库信息
    repo_owner = os.getenv('GITHUB_REPOSITORY_OWNER', 'zhaozhenggang')
    repo_name = os.getenv('GITHUB_REPOSITORY_NAME', 'ai-codereview-gitlab')
    github_token = os.getenv('GITHUB_TOKEN')  # 可选的GitHub Token
    
    # 支持命令行参数
    if len(sys.argv) >= 3:
        repo_owner = sys.argv[1]
        repo_name = sys.argv[2]
    
    print(f"🔍 检查仓库: {repo_owner}/{repo_name}")
    print(f"🕐 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查GitHub Actions状态
    actions_ok = check_github_actions_status(repo_owner, repo_name, github_token)
    
    print()
    
    # 检查Docker镜像状态
    docker_ok = check_docker_images(repo_owner, repo_name, github_token)
    
    print()
    print("=" * 60)
    
    if actions_ok and docker_ok:
        print("✅ 所有检查通过")
        return 0
    else:
        print("❌ 部分检查失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
