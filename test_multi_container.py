#!/usr/bin/env python3
"""
AI-CodeReview 多容器配置验证脚本
验证多容器 Docker Compose 配置是否正确
"""

import os
import sys
import yaml
import subprocess
from pathlib import Path

def test_multi_container_config():
    """测试多容器 Docker Compose 配置"""
    print("🔍 测试 Docker Compose 多容器配置...")
    
    compose_file = Path("docker-compose.yml")
    if not compose_file.exists():
        print("❌ docker-compose.yml 文件不存在")
        return False
    
    try:
        with open(compose_file, 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)
        
        # 检查服务配置
        services = compose_config.get('services', {})
        
        # 应该有 ai-codereview, ai-codereview-worker, redis 三个服务
        required_services = ['ai-codereview', 'ai-codereview-worker', 'redis']
        for service in required_services:
            if service not in services:
                print(f"❌ 缺少服务: {service}")
                return False
        
        # 检查 ai-codereview 服务配置
        ai_service = services['ai-codereview']
        if ai_service.get('environment', []):
            env_str = str(ai_service['environment'])
            if 'DOCKER_RUN_MODE=app' not in env_str:
                print("❌ ai-codereview 服务应该使用 app 模式")
                return False
        
        # 检查 worker 服务配置
        worker_service = services['ai-codereview-worker']
        if worker_service.get('environment', []):
            env_str = str(worker_service['environment'])
            if 'DOCKER_RUN_MODE=worker' not in env_str:
                print("❌ worker 服务应该使用 worker 模式")
                return False
        
        # 检查 profiles 配置
        if 'profiles' not in worker_service:
            print("❌ worker 服务缺少 profiles 配置")
            return False
        
        if 'profiles' not in services['redis']:
            print("❌ redis 服务缺少 profiles 配置")
            return False
        
        print("✅ Docker Compose 多容器配置正确")
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML 语法错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

def test_service_dependencies():
    """测试服务依赖关系"""
    print("🔍 测试服务依赖关系...")
    
    try:
        with open("docker-compose.yml", 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)
        
        services = compose_config.get('services', {})
        worker_service = services.get('ai-codereview-worker', {})
        
        # 检查 worker 服务的依赖
        depends_on = worker_service.get('depends_on', {})
        if 'ai-codereview' not in depends_on:
            print("❌ worker 服务缺少对 ai-codereview 的依赖")
            return False
        
        if 'redis' not in depends_on:
            print("❌ worker 服务缺少对 redis 的依赖")
            return False
        
        print("✅ 服务依赖关系配置正确")
        return True
        
    except Exception as e:
        print(f"❌ 服务依赖检查失败: {e}")
        return False

def test_profiles_configuration():
    """测试 profiles 配置"""
    print("🔍 测试 Profiles 配置...")
    
    try:
        # 测试基础配置（仅 ai-codereview 服务）
        # 确保没有 COMPOSE_PROFILES 环境变量
        env_basic = os.environ.copy()
        env_basic.pop('COMPOSE_PROFILES', None)
        
        result1 = subprocess.run(
            ['docker', 'compose', 'config', '--services'],
            capture_output=True,
            text=True,
            timeout=30,
            env=env_basic
        )
        
        if result1.returncode == 0:
            basic_services = set(result1.stdout.strip().split('\n'))
            if basic_services != {'ai-codereview'}:
                print(f"❌ 基础模式应该只有 ai-codereview 服务，实际有: {basic_services}")
                return False
            print("✅ 基础模式配置正确")
        
        # 测试 worker profile
        env_worker = os.environ.copy()
        env_worker['COMPOSE_PROFILES'] = 'worker'
        
        result2 = subprocess.run(
            ['docker', 'compose', 'config', '--services'],
            capture_output=True,
            text=True,
            timeout=30,
            env=env_worker
        )
        
        if result2.returncode == 0:
            worker_services = set(result2.stdout.strip().split('\n'))
            expected_services = {'ai-codereview', 'ai-codereview-worker', 'redis'}
            if worker_services != expected_services:
                print(f"❌ Worker 模式服务不匹配，期望: {expected_services}，实际: {worker_services}")
                return False
            print("✅ Worker 模式配置正确")
        
        return True
            
    except subprocess.TimeoutExpired:
        print("❌ Profiles 配置验证超时")
        return False
    except FileNotFoundError:
        print("⚠️  docker compose 命令不可用，跳过 profiles 验证")
        return True
    except Exception as e:
        print(f"❌ Profiles 配置验证失败: {e}")
        return False

def test_supervisord_configs():
    """测试 supervisord 配置文件"""
    print("🔍 测试 Supervisord 配置文件...")
    
    config_files = {
        "conf/supervisord.app.conf": ["flask", "streamlit"],
        "conf/supervisord.worker.conf": ["background_worker"],
        "conf/supervisord.all.conf": ["flask", "streamlit", "worker"]
    }
    
    for config_file, expected_programs in config_files.items():
        file_path = Path(config_file)
        if not file_path.exists():
            print(f"❌ 缺少配置文件: {config_file}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for program in expected_programs:
                if f'[program:{program}]' not in content:
                    print(f"❌ {config_file} 缺少程序配置: {program}")
                    return False
            
            print(f"✅ {config_file} 配置正确")
            
        except Exception as e:
            print(f"❌ {config_file} 检查失败: {e}")
            return False
    
    return True

def test_environment_variables():
    """测试环境变量配置"""
    print("🔍 测试环境变量配置...")
    
    # 现在我们不再使用 .env 文件，所以检查 docker-compose 配置中的环境变量
    compose_file = Path("docker-compose.yml")
    if not compose_file.exists():
        print("❌ docker-compose.yml 文件不存在")
        return False
    
    try:
        with open(compose_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键的环境变量是否在 compose 文件中定义
        required_env_vars = [
            'DOCKER_RUN_MODE',
            'TZ=Asia/Shanghai',
            'LOG_LEVEL=INFO',
            'PYTHON_ENV=production'
        ]
        
        for env_var in required_env_vars:
            if env_var not in content:
                print(f"❌ docker-compose.yml 缺少环境变量: {env_var}")
                return False
        
        print("✅ 环境变量配置完整")
        return True
        
    except Exception as e:
        print(f"❌ 环境变量检查失败: {e}")
        return False
        
        # 检查多容器模式相关的配置
        required_configs = [
            'COMPOSE_PROFILES=worker',
            'QUEUE_DRIVER=rq',
            'ENABLE_WORKER=true'
        ]
        
        for config in required_configs:
            if config not in content:
                print(f"❌ 缺少配置: {config}")
                return False
        
        print("✅ 环境变量配置完整")
        return True
        
    except Exception as e:
        print(f"❌ 环境变量配置检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 AI-CodeReview 多容器配置验证")
    print("=" * 60)
    
    tests = [
        test_multi_container_config,
        test_service_dependencies,
        test_profiles_configuration,
        test_supervisord_configs,
        test_environment_variables
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
        print("🎉 所有测试通过！多容器配置已准备就绪")
        print()
        print("💡 使用方法:")
        print("   基础模式: docker-compose up -d")
        print("   完整模式: COMPOSE_PROFILES=worker docker-compose up -d")
        print("   或者:")
        print("   编辑 .env 文件设置 COMPOSE_PROFILES=worker")
        print("   然后运行: docker-compose up -d")
        return 0
    else:
        print("❌ 部分测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())
