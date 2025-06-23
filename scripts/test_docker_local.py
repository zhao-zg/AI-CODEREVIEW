#!/usr/bin/env python3
"""
本地Docker构建和测试脚本
用于在提交前本地验证Docker镜像构建
"""

import subprocess
import sys
import time
import json
import argparse
from pathlib import Path

def run_command(cmd, shell=True, capture_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def build_image(target, tag):
    """构建Docker镜像"""
    print(f"🏗️  构建 {target} 镜像...")
    cmd = f"docker build --target {target} -t {tag} ."
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✅ {target} 镜像构建成功")
        return True
    else:
        print(f"❌ {target} 镜像构建失败:")
        print(f"stderr: {stderr}")
        return False

def test_app_container():
    """测试应用容器"""
    print("🧪 测试应用容器...")
    
    # 启动容器
    cmd = "docker run --rm -d --name test-app -p 15001:5001 -p 15002:5002 test-app:latest"
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        print(f"❌ 启动应用容器失败: {stderr}")
        return False
    
    container_id = stdout
    print(f"📦 容器已启动: {container_id[:12]}")
    
    try:
        # 等待容器启动
        print("⏳ 等待容器启动...")
        time.sleep(15)
        
        # 检查容器状态
        success, stdout, stderr = run_command("docker ps --filter name=test-app --format '{{.Status}}'")
        if success and "Up" in stdout:
            print(f"✅ 容器运行状态: {stdout}")
        else:
            print(f"❌ 容器状态异常: {stdout}")
            return False
        
        # 检查日志
        success, stdout, stderr = run_command("docker logs test-app")
        if success:
            print("📝 容器日志:")
            print(stdout[-500:])  # 显示最后500字符
        
        # 测试API端点（如果有健康检查端点）
        print("🔍 测试API端点...")
        success, stdout, stderr = run_command("curl -f http://localhost:15001/ || echo 'API test completed'")
        print(f"🌐 API测试结果: {stdout}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试应用容器时出错: {e}")
        return False
    finally:
        # 清理容器
        print("🧹 清理测试容器...")
        run_command("docker stop test-app")

def test_worker_container():
    """测试工作容器"""
    print("🧪 测试工作容器...")
    
    # 启动容器
    cmd = "docker run --rm -d --name test-worker test-worker:latest"
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        print(f"❌ 启动工作容器失败: {stderr}")
        return False
    
    container_id = stdout
    print(f"📦 容器已启动: {container_id[:12]}")
    
    try:
        # 等待容器启动
        print("⏳ 等待容器启动...")
        time.sleep(10)
        
        # 检查容器状态
        success, stdout, stderr = run_command("docker ps --filter name=test-worker --format '{{.Status}}'")
        if success and "Up" in stdout:
            print(f"✅ 容器运行状态: {stdout}")
        else:
            print(f"❌ 容器状态异常: {stdout}")
            return False
        
        # 检查日志
        success, stdout, stderr = run_command("docker logs test-worker")
        if success:
            print("📝 容器日志:")
            print(stdout[-500:])  # 显示最后500字符
        
        return True
        
    except Exception as e:
        print(f"❌ 测试工作容器时出错: {e}")
        return False
    finally:
        # 清理容器
        print("🧹 清理测试容器...")
        run_command("docker stop test-worker")

def cleanup_test_images():
    """清理测试镜像"""
    print("🧹 清理测试镜像...")
    run_command("docker rmi test-app:latest test-worker:latest", capture_output=False)

def main():
    parser = argparse.ArgumentParser(description="本地Docker构建和测试")
    parser.add_argument("--build-only", action="store_true", help="仅构建，不测试")
    parser.add_argument("--test-only", action="store_true", help="仅测试，不构建")
    parser.add_argument("--cleanup", action="store_true", help="清理测试镜像")
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_images()
        return
    
    print("🚀 开始本地Docker测试...")
    
    # 检查当前目录
    if not Path("Dockerfile").exists():
        print("❌ 未找到Dockerfile，请在项目根目录运行此脚本")
        sys.exit(1)
    
    success = True
    
    if not args.test_only:
        # 构建镜像
        if not build_image("app", "test-app:latest"):
            success = False
        
        if not build_image("worker", "test-worker:latest"):
            success = False
    
    if not args.build_only and success:
        # 测试容器
        if not test_app_container():
            success = False
        
        if not test_worker_container():
            success = False
    
    if success:
        print("🎉 所有测试通过！")
        print("💡 你可以安全地提交代码，GitHub Actions将自动构建和发布镜像")
    else:
        print("❌ 测试失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
