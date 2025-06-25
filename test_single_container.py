#!/usr/bin/env python3
"""
AI-CodeReview 单容器配置验证脚本
验证新的单容器 Docker Compose 配置是否正确
"""

import os
import sys
import yaml
import subprocess
from pathlib import Path

def test_docker_compose_config():
    """测试 Docker Compose 配置文件"""
    print("🔍 测试 Docker Compose 单容器配置...")
    
    compose_file = Path("docker-compose.single.yml")
    if not compose_file.exists():
        print("❌ docker-compose.single.yml 文件不存在")
        return False
    
    try:
        with open(compose_file, 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)
        
        # 检查服务配置
        services = compose_config.get('services', {})
        
        # 应该只有 ai-codereview 和可选的 redis 服务
        if 'ai-codereview' not in services:
            print("❌ 缺少 ai-codereview 服务")
            return False
        
        # 检查 ai-codereview 服务配置
        ai_service = services['ai-codereview']
          # 检查环境变量
        env_vars = ai_service.get('environment', [])
        required_env = ['DOCKER_RUN_MODE', 'ENABLE_WORKER']
        
        env_str = str(env_vars)
        for env in required_env:
            if env not in env_str:
                print(f"❌ 缺少环境变量: {env}")
                return False
        
        # 检查运行模式是否为 all
        has_all_mode = False
        for env_var in env_vars:
            if isinstance(env_var, str) and 'DOCKER_RUN_MODE=all' in env_var:
                has_all_mode = True
                break
        
        if not has_all_mode:
            print("❌ DOCKER_RUN_MODE 未设置为 all")
            return False
        
        # 检查端口映射
        ports = ai_service.get('ports', [])
        if len(ports) < 2:
            print("❌ 端口映射配置不完整")
            return False
        
        print("✅ Docker Compose 单容器配置正确")
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML 语法错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

def test_supervisord_config():
    """测试 supervisord 配置文件"""
    print("🔍 测试 Supervisord 配置文件...")
    
    config_files = [
        "conf/supervisord.app.conf",
        "conf/supervisord.worker.conf", 
        "conf/supervisord.all.conf"
    ]
    
    for config_file in config_files:
        file_path = Path(config_file)
        if not file_path.exists():
            print(f"❌ 缺少配置文件: {config_file}")
            return False
        
        print(f"✅ 存在: {config_file}")
    
    # 检查 supervisord.all.conf 内容
    all_conf = Path("conf/supervisord.all.conf")
    try:
        with open(all_conf, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_programs = ['flask', 'streamlit', 'worker']
        for program in required_programs:
            if f'[program:{program}]' not in content:
                print(f"❌ supervisord.all.conf 缺少程序配置: {program}")
                return False
        
        print("✅ Supervisord 配置文件完整")
        return True
        
    except Exception as e:
        print(f"❌ Supervisord 配置检查失败: {e}")
        return False

def test_background_worker():
    """测试后台任务处理器"""
    print("🔍 测试后台任务处理器...")
    
    worker_script = Path("scripts/background_worker.py")
    if not worker_script.exists():
        print("❌ 后台任务处理器脚本不存在")
        return False
    
    try:
        # 简单的语法检查
        with open(worker_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_functions = ['run_rq_worker', 'run_svn_worker', 'run_background_tasks']
        for func in required_functions:
            if f'def {func}(' not in content:
                print(f"❌ 后台任务处理器缺少函数: {func}")
                return False
        
        print("✅ 后台任务处理器配置正确")
        return True
        
    except Exception as e:
        print(f"❌ 后台任务处理器检查失败: {e}")
        return False

def test_docker_compose_syntax():
    """测试 Docker Compose 语法"""
    print("🔍 测试 Docker Compose 语法...")
    
    try:
        result = subprocess.run(
            ['docker-compose', '-f', 'docker-compose.single.yml', 'config', '--quiet'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Docker Compose 语法验证通过")
            return True
        else:
            print(f"❌ Docker Compose 语法错误: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Docker Compose 验证超时")
        return False
    except FileNotFoundError:
        print("⚠️  docker-compose 命令不可用，跳过语法验证")
        return True
    except Exception as e:
        print(f"❌ Docker Compose 语法验证失败: {e}")
        return False

def test_environment_config():
    """测试环境变量配置"""
    print("🔍 测试环境变量配置...")
    
    env_example = Path(".env.docker.example")
    if not env_example.exists():
        print("❌ .env.docker.example 文件不存在")
        return False
    
    try:
        with open(env_example, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查新增的配置项
        required_vars = [
            'ENABLE_WORKER',
            'QUEUE_DRIVER',
            'SVN_CHECK_ENABLED',
            'SVN_CHECK_INTERVAL'
        ]
        
        for var in required_vars:
            if var not in content:
                print(f"❌ 缺少环境变量配置: {var}")
                return False
        
        print("✅ 环境变量配置完整")
        return True
        
    except Exception as e:
        print(f"❌ 环境变量配置检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 AI-CodeReview 单容器配置验证")
    print("=" * 60)
    
    tests = [
        test_docker_compose_config,
        test_supervisord_config,
        test_background_worker,
        test_environment_config,
        test_docker_compose_syntax
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！单容器配置已准备就绪")
        print()
        print("💡 使用方法:")
        print("   基础模式: docker-compose up -d")
        print("   Redis模式: COMPOSE_PROFILES=redis docker-compose up -d")
        return 0
    else:
        print("❌ 部分测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())
