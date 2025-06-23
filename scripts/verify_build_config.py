#!/usr/bin/env python3
"""
自动构建配置验证脚本
验证GitHub Actions和Docker相关配置是否正确
"""

import os
import json
import yaml
from pathlib import Path

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}不存在: {file_path}")
        return False

def check_yaml_valid(file_path):
    """检查YAML文件是否有效"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print(f"✅ YAML语法正确: {file_path}")
        return True
    except Exception as e:
        print(f"❌ YAML语法错误: {file_path} - {e}")
        return False

def check_docker_build_config():
    """检查Docker构建配置"""
    config_file = ".github/workflows/docker-build.yml"
    
    if not check_file_exists(config_file, "Docker构建工作流"):
        return False
    
    if not check_yaml_valid(config_file):
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)        # 检查关键配置
        on_config = config.get("on", {})
        has_push = "push" in on_config
        has_pr = "pull_request" in on_config
        
        checks = [
            ("触发条件", has_push or has_pr),
            ("环境变量", "env" in config and "REGISTRY" in config["env"]),
            ("作业定义", "jobs" in config and "build-and-push" in config["jobs"]),
            ("权限设置", "permissions" in config["jobs"]["build-and-push"]),
            ("多阶段构建", "app" in str(config) and "worker" in str(config)),
        ]
        
        all_passed = True
        for check_name, condition in checks:
            if condition:
                print(f"✅ {check_name}配置正确")
            else:
                print(f"❌ {check_name}配置缺失")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False

def check_dockerfile():
    """检查Dockerfile配置"""
    if not check_file_exists("Dockerfile", "Dockerfile"):
        return False
    
    try:
        with open("Dockerfile", 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("基础镜像", "FROM python:" in content),
            ("多阶段构建", "AS base" in content and "AS app" in content and "AS worker" in content),
            ("工作目录", "WORKDIR" in content),
            ("依赖安装", "requirements.txt" in content),
            ("端口暴露", "EXPOSE" in content),
        ]
        
        all_passed = True
        for check_name, condition in checks:
            if condition:
                print(f"✅ Dockerfile {check_name}配置正确")
            else:
                print(f"❌ Dockerfile {check_name}配置缺失")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 读取Dockerfile失败: {e}")
        return False

def check_docker_compose():
    """检查docker-compose配置"""
    if not check_file_exists("docker-compose.yml", "Docker Compose文件"):
        return False
    
    if not check_yaml_valid("docker-compose.yml"):
        return False
    
    try:
        with open("docker-compose.yml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查镜像配置
        if "services" in config and "app" in config["services"]:
            image = config["services"]["app"].get("image", "")
            if "ghcr.io" in image and "zhao-zg" in image:
                print("✅ Docker Compose镜像配置正确")
                return True
            else:
                print(f"❌ Docker Compose镜像配置错误: {image}")
                return False
        else:
            print("❌ Docker Compose服务配置缺失")
            return False
            
    except Exception as e:
        print(f"❌ 读取docker-compose.yml失败: {e}")
        return False

def check_scripts():
    """检查辅助脚本"""
    scripts = [
        ("scripts/test_docker_local.py", "本地Docker测试脚本"),
        ("scripts/release.py", "版本发布脚本"),
        ("scripts/check_ci_status.py", "CI状态检查脚本"),
    ]
    
    all_passed = True
    for script_path, description in scripts:
        if not check_file_exists(script_path, description):
            all_passed = False
    
    return all_passed

def check_documentation():
    """检查文档"""
    docs = [
        ("docs/auto-build-guide.md", "自动构建指南"),
        ("DOCKER_AUTO_BUILD.md", "Docker自动构建说明"),
    ]
    
    all_passed = True
    for doc_path, description in docs:
        if not check_file_exists(doc_path, description):
            all_passed = False
    
    return all_passed

def check_ignore_files():
    """检查忽略文件配置"""
    if not check_file_exists(".dockerignore", "Docker忽略文件"):
        return False
    
    try:
        with open(".dockerignore", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键排除项
        essential_ignores = [".git", "__pycache__", "*.pyc", ".pytest_cache"]
        missing_ignores = []
        
        for ignore_item in essential_ignores:
            if ignore_item not in content:
                missing_ignores.append(ignore_item)
        
        if missing_ignores:
            print(f"⚠️  .dockerignore可能缺少: {', '.join(missing_ignores)}")
        else:
            print("✅ .dockerignore配置完整")
        
        return True
        
    except Exception as e:
        print(f"❌ 读取.dockerignore失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 验证自动构建配置...")
    print("=" * 50)
    
    checks = [
        ("GitHub Actions工作流", check_docker_build_config),
        ("Dockerfile", check_dockerfile),
        ("Docker Compose", check_docker_compose),
        ("辅助脚本", check_scripts),
        ("文档", check_documentation),
        ("忽略文件", check_ignore_files),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n📋 检查{check_name}...")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有配置检查通过！")
        print("💡 自动构建功能已完全配置，提交代码后将自动构建Docker镜像")
        print("🌐 监控构建状态: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB/actions")
        print("📦 镜像地址: ghcr.io/zhao-zg/ai-codereview-gitlab")
    else:
        print("❌ 部分配置存在问题，请检查上述错误信息")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
