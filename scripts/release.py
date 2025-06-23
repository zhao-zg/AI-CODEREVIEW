#!/usr/bin/env python3
"""
版本发布脚本
用于创建Git标签、GitHub Release，并触发Docker镜像构建
"""

import subprocess
import sys
import json
import argparse
import re
from datetime import datetime
from pathlib import Path

def run_command(cmd, shell=True, capture_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def get_current_version():
    """获取当前版本号"""
    # 尝试从git标签获取
    success, stdout, stderr = run_command("git describe --tags --abbrev=0")
    if success and stdout:
        return stdout.replace('v', '')
    
    # 如果没有标签，返回默认版本
    return "0.1.0"

def increment_version(version, increment_type):
    """递增版本号"""
    parts = version.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    
    major, minor, patch = map(int, parts)
    
    if increment_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid increment type: {increment_type}")
    
    return f"{major}.{minor}.{patch}"

def validate_version(version):
    """验证版本号格式"""
    pattern = r'^v?\d+\.\d+\.\d+$'
    return re.match(pattern, version) is not None

def get_recent_commits(since_tag=None):
    """获取最近的提交信息"""
    if since_tag:
        cmd = f"git log {since_tag}..HEAD --oneline --no-merges"
    else:
        cmd = "git log --oneline --no-merges -10"
    
    success, stdout, stderr = run_command(cmd)
    if success:
        return stdout.split('\n') if stdout else []
    return []

def generate_changelog(commits):
    """生成变更日志"""
    if not commits:
        return "- 初始版本"
    
    changelog = []
    for commit in commits:
        if commit.strip():
            # 简单的提交信息处理
            parts = commit.split(' ', 1)
            if len(parts) > 1:
                message = parts[1]
                if message.startswith(('feat:', 'feature:')):
                    changelog.append(f"- ✨ {message}")
                elif message.startswith(('fix:', 'bugfix:')):
                    changelog.append(f"- 🐛 {message}")
                elif message.startswith(('docs:', 'doc:')):
                    changelog.append(f"- 📚 {message}")
                elif message.startswith(('style:', 'ui:')):
                    changelog.append(f"- 💄 {message}")
                elif message.startswith(('refactor:', 'refact:')):
                    changelog.append(f"- ♻️ {message}")
                elif message.startswith(('perf:', 'optimize:')):
                    changelog.append(f"- ⚡ {message}")
                elif message.startswith(('test:', 'tests:')):
                    changelog.append(f"- 🧪 {message}")
                elif message.startswith(('ci:', 'cd:')):
                    changelog.append(f"- 👷 {message}")
                else:
                    changelog.append(f"- 🔧 {message}")
    
    return '\n'.join(changelog[:20])  # 限制最多20条

def create_git_tag(version, message):
    """创建Git标签"""
    tag = f"v{version}"
    cmd = f'git tag -a {tag} -m "{message}"'
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✅ 已创建标签: {tag}")
        return tag
    else:
        print(f"❌ 创建标签失败: {stderr}")
        return None

def push_tag(tag):
    """推送标签到远程仓库"""
    cmd = f"git push origin {tag}"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✅ 已推送标签: {tag}")
        return True
    else:
        print(f"❌ 推送标签失败: {stderr}")
        return False

def create_github_release(tag, changelog):
    """创建GitHub Release（需要GitHub CLI）"""
    # 检查是否安装了GitHub CLI
    success, stdout, stderr = run_command("gh --version")
    if not success:
        print("⚠️  未安装GitHub CLI，跳过创建GitHub Release")
        print("💡 请手动在网页上创建Release，或安装GitHub CLI")
        return False
    
    # 创建Release
    release_notes = f"""## 🚀 版本 {tag}

### 📋 更新内容

{changelog}

### 🐳 Docker镜像

此版本的Docker镜像将自动构建并发布到GitHub Container Registry:

- `ghcr.io/zhao-zg/ai-codereview-gitlab:{tag.replace('v', '')}`
- `ghcr.io/zhao-zg/ai-codereview-gitlab:{tag.replace('v', '')}-worker`
- `ghcr.io/zhao-zg/ai-codereview-gitlab:latest`

### 📦 使用方法

```bash
# 拉取最新镜像
docker pull ghcr.io/zhao-zg/ai-codereview-gitlab:latest

# 或者使用docker-compose
docker-compose up -d
```

### 🔗 相关链接

- [部署指南](./doc/deployment_guide.md)
- [使用文档](./doc/ui_guide.md)
- [FAQ](./doc/faq.md)
"""
    
    cmd = f'gh release create {tag} --title "Release {tag}" --notes "{release_notes}"'
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✅ 已创建GitHub Release: {tag}")
        return True
    else:
        print(f"❌ 创建GitHub Release失败: {stderr}")
        return False

def check_git_status():
    """检查Git状态"""
    # 检查是否有未提交的更改
    success, stdout, stderr = run_command("git status --porcelain")
    if success and stdout:
        print("❌ 存在未提交的更改，请先提交所有更改")
        print("未提交的文件:")
        print(stdout)
        return False
    
    # 检查是否在正确的分支
    success, stdout, stderr = run_command("git branch --show-current")
    if success:
        current_branch = stdout
        if current_branch not in ['main', 'master']:
            print(f"⚠️  当前分支是 '{current_branch}'，建议在 'main' 或 'master' 分支发布")
            response = input("是否继续? (y/N): ")
            if response.lower() != 'y':
                return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="版本发布脚本")
    parser.add_argument("--version", help="指定版本号 (例如: 1.2.3)")
    parser.add_argument("--increment", choices=["major", "minor", "patch"], 
                       default="patch", help="版本递增类型 (默认: patch)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际创建标签")
    parser.add_argument("--skip-github-release", action="store_true", help="跳过创建GitHub Release")
    args = parser.parse_args()
    
    print("🚀 版本发布流程开始...")
    
    # 检查Git状态
    if not check_git_status():
        sys.exit(1)
    
    # 确定版本号
    if args.version:
        new_version = args.version.replace('v', '')
    else:
        current_version = get_current_version()
        new_version = increment_version(current_version, args.increment)
        print(f"📊 当前版本: {current_version}")
    
    if not validate_version(new_version):
        print(f"❌ 无效的版本号格式: {new_version}")
        sys.exit(1)
    
    print(f"🎯 新版本: {new_version}")
    
    # 获取变更日志
    current_tag = f"v{get_current_version()}"
    commits = get_recent_commits(current_tag if current_tag != f"v{new_version}" else None)
    changelog = generate_changelog(commits)
    
    print(f"\n📋 变更日志:")
    print(changelog)
    
    if args.dry_run:
        print("\n🔍 预览模式，不会实际创建标签和发布")
        print(f"将要创建的标签: v{new_version}")
        print(f"将要推送到远程仓库")
        if not args.skip_github_release:
            print(f"将要创建GitHub Release")
        return
    
    # 确认发布
    print(f"\n❓ 确认发布版本 v{new_version}?")
    response = input("继续? (y/N): ")
    if response.lower() != 'y':
        print("❌ 发布已取消")
        sys.exit(1)
    
    # 创建标签
    tag = create_git_tag(new_version, f"Release version {new_version}")
    if not tag:
        sys.exit(1)
    
    # 推送标签
    if not push_tag(tag):
        sys.exit(1)
      # 创建GitHub Release
    if not args.skip_github_release:
        create_github_release(tag, changelog)
    
    print(f"\n🎉 版本 {tag} 发布完成！")
    print(f"🔄 GitHub Actions将自动构建和发布Docker镜像")
    print(f"🌐 检查构建状态: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB/actions")
    print(f"📦 Docker镜像将发布到: ghcr.io/zhao-zg/ai-codereview-gitlab")

if __name__ == "__main__":
    main()
