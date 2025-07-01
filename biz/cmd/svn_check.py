#!/usr/bin/env python3
"""
SVN代码审查命令行工具
"""
import argparse
import json
import os
import sys
from dotenv import load_dotenv
from biz.utils.default_config import get_env_with_default, get_env_int

# 加载环境变量
load_dotenv("conf/.env")

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biz.svn.svn_worker import handle_svn_changes, handle_multiple_svn_repositories
from biz.utils.log import logger


def main():
    parser = argparse.ArgumentParser(description='SVN代码审查工具')
    
    # 多仓库支持
    parser.add_argument('--repo', type=str, help='指定要检查的仓库名称（用于多仓库配置）')
    parser.add_argument('--list-repos', action='store_true', help='列出所有配置的仓库')
    
    # 单仓库支持（向后兼容）
    parser.add_argument('--svn-url', type=str, help='SVN远程仓库URL')
    parser.add_argument('--svn-path', type=str, help='SVN本地路径')
    parser.add_argument('--username', type=str, help='SVN用户名')
    parser.add_argument('--password', type=str, help='SVN密码')
    
    parser.add_argument('--hours', type=int, default=24, help='检查最近N小时的提交（默认24小时）')
    parser.add_argument('--check-only', action='store_true', help='仅检查不审查')
    
    args = parser.parse_args()
    
    # 设置审查模式
    if args.check_only:
        os.environ['SVN_REVIEW_ENABLED'] = '0'
        print("运行模式: 仅检查变更，不进行代码审查")
    else:
        print("运行模式: 检查变更并进行代码审查")
      # 获取多仓库配置
    svn_repositories_config = get_env_with_default('SVN_REPOSITORIES')
    try:
        repositories = json.loads(svn_repositories_config)
    except json.JSONDecodeError as e:
        repositories = []
        print(f"警告: SVN仓库配置JSON解析失败: {e}")
    
    # 列出仓库
    if args.list_repos:
        if repositories:
            print("配置的SVN仓库:")
            for repo in repositories:
                name = repo.get('name', 'unknown')
                url = repo.get('remote_url', 'unknown')
                print(f"  - {name}: {url}")
        else:
            print("没有配置多仓库，检查单仓库配置...")
            svn_remote_url = get_env_with_default('SVN_REMOTE_URL')
            if svn_remote_url:
                print(f"  - legacy: {svn_remote_url}")
            else:
                print("  没有配置任何仓库")
        return
    
    # 检查特定仓库
    if args.repo:
        if not repositories:
            print("错误: 没有配置多仓库，无法检查指定仓库")
            sys.exit(1)
        
        target_repo = None
        for repo in repositories:
            if repo.get('name') == args.repo:
                target_repo = repo
                break
        
        if not target_repo:
            print(f"错误: 未找到名为 '{args.repo}' 的仓库配置")
            print("可用的仓库:")
            for repo in repositories:
                print(f"  - {repo.get('name', 'unknown')}")
            sys.exit(1)
        
        # 执行单个仓库检查
        remote_url = target_repo.get('remote_url')
        local_path = target_repo.get('local_path')
        username = target_repo.get('username')
        password = target_repo.get('password')
        repo_hours = args.hours or target_repo.get('check_hours', 24)
        
        print(f"开始检查仓库: {args.repo}")
        print(f"远程URL: {remote_url}")
        print(f"本地路径: {local_path}")
        print(f"检查时间范围: 最近{repo_hours}小时")
        
        try:
            handle_svn_changes(remote_url, local_path, username, password, repo_hours, 100, args.repo, "manual")
            print("SVN检查完成")
        except Exception as e:
            logger.error(f"SVN检查失败: {e}")
            print(f"SVN检查失败: {e}")
            sys.exit(1)
        return
    
    # 检查所有仓库
    if repositories:
        print(f"开始检查所有仓库（共{len(repositories)}个）")
        print(f"检查时间范围: 最近{args.hours}小时")        
        # 获取限制参数
        check_limit = get_env_int('SVN_CHECK_LIMIT')
        
        try:
            handle_multiple_svn_repositories(svn_repositories_config, args.hours, check_limit, "manual")
            print("所有仓库检查完成")
        except Exception as e:
            logger.error(f"多仓库SVN检查失败: {e}")
            print(f"多仓库SVN检查失败: {e}")
            sys.exit(1)
        return
      # 回退到单仓库模式（向后兼容）
    svn_remote_url = args.svn_url or get_env_with_default('SVN_REMOTE_URL')
    svn_local_path = args.svn_path or get_env_with_default('SVN_LOCAL_PATH')
    svn_username = args.username or get_env_with_default('SVN_USERNAME')
    svn_password = args.password or get_env_with_default('SVN_PASSWORD')
    
    if not svn_remote_url or not svn_local_path:
        print("错误: 未配置SVN仓库")
        print("请配置 SVN_REPOSITORIES 环境变量或使用 --svn-url 和 --svn-path 参数")
        sys.exit(1)
    
    print(f"开始检查SVN变更（单仓库模式）...")
    print(f"远程URL: {svn_remote_url}")
    print(f"本地路径: {svn_local_path}")
    print(f"检查时间范围: 最近{args.hours}小时")
    print(f"用户名: {svn_username or '未设置'}")
      # 获取限制参数
    check_limit = get_env_int('SVN_CHECK_LIMIT')
    
    try:
        handle_svn_changes(svn_remote_url, svn_local_path, svn_username, svn_password, args.hours, check_limit, None, "manual")
        print("SVN检查完成")
    except Exception as e:
        logger.error(f"SVN检查失败: {e}")
        print(f"SVN检查失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
