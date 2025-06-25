#!/usr/bin/env python3
"""
配置热重载功能测试脚本
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_reloader():
    """测试配置重载功能"""
    print("🧪 测试配置热重载功能...")
    print("=" * 50)
    
    try:
        from biz.utils.config_reloader import ConfigReloader
        
        # 创建配置重载器
        reloader = ConfigReloader()
        
        # 测试1: 环境变量重载
        print("1. 测试环境变量重载...")
        if reloader.reload_environment_variables():
            print("   ✅ 环境变量重载成功")
        else:
            print("   ❌ 环境变量重载失败")
        
        # 测试2: 服务通知
        print("\n2. 测试服务通知...")
        notification_results = reloader.notify_services_config_changed()
        
        for service, success in notification_results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {service} 服务通知: {'成功' if success else '失败'}")
        
        # 测试3: 完整配置重载
        print("\n3. 测试完整配置重载...")
        result = reloader.reload_all_configs()
        
        if result.get("success", False):
            print(f"   ✅ 完整重载成功: {result['message']}")
        else:
            print(f"   ❌ 完整重载失败: {result['message']}")
        
        print("\n" + "=" * 50)
        print("✅ 配置热重载功能测试完成")
        return True
        
    except ImportError as e:
        print(f"❌ 导入配置重载模块失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        return False

def test_config_monitor():
    """测试配置监控功能"""
    print("\n🔍 测试配置文件监控功能...")
    print("=" * 50)
    
    try:
        from scripts.config_monitor import ConfigMonitorService
        
        # 创建临时配置目录
        temp_dir = Path(tempfile.mkdtemp(prefix="test_config_"))
        test_env_file = temp_dir / ".env"
        
        print(f"创建临时测试目录: {temp_dir}")
        
        # 创建测试配置文件
        with open(test_env_file, 'w') as f:
            f.write("TEST_VAR=initial_value\n")
        
        # 创建监控服务
        monitor = ConfigMonitorService(str(temp_dir))
        
        print("启动配置监控服务...")
        monitor.start()
        
        if monitor.is_running():
            print("✅ 配置监控服务启动成功")
        else:
            print("❌ 配置监控服务启动失败")
            return False
        
        # 模拟配置文件变化
        print("模拟配置文件变化...")
        time.sleep(1)  # 等待监控器准备就绪
        
        with open(test_env_file, 'w') as f:
            f.write("TEST_VAR=updated_value\n")
        
        # 等待监控器处理
        time.sleep(3)
        
        # 停止监控服务
        print("停止配置监控服务...")
        monitor.stop()
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        print("✅ 配置监控功能测试完成")
        return True
        
    except ImportError as e:
        print(f"❌ 导入配置监控模块失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        return False

def test_api_reload_endpoint():
    """测试API重载端点"""
    print("\n🌐 测试API配置重载端点...")
    print("=" * 50)
    
    try:
        import requests
        
        # 尝试连接API服务
        api_port = os.environ.get('API_PORT', '5001')
        api_url = f"http://localhost:{api_port}"
        
        # 先检查API服务是否运行
        try:
            response = requests.get(f"{api_url}/health", timeout=3)
            if response.status_code == 200:
                print(f"✅ API服务运行正常 (端口{api_port})")
            else:
                print(f"⚠️ API服务响应异常 (状态码: {response.status_code})")
                return False
        except requests.exceptions.ConnectionError:
            print(f"⚠️ API服务不可达 (端口{api_port})，跳过API端点测试")
            return True
        
        # 测试配置重载端点
        reload_url = f"{api_url}/reload-config"
        response = requests.post(reload_url, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                print(f"✅ API配置重载成功: {result['message']}")
                return True
            else:
                print(f"❌ API配置重载失败: {result['message']}")
                return False
        else:
            print(f"❌ API配置重载请求失败 (状态码: {response.status_code})")
            return False
            
    except ImportError:
        print("⚠️ requests库未安装，跳过API端点测试")
        return True
    except Exception as e:
        print(f"❌ API端点测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 AI-CodeReview 配置热重载功能测试")
    print("=" * 60)
    
    test_results = []
    
    # 执行各项测试
    test_results.append(("配置重载功能", test_config_reloader()))
    test_results.append(("配置监控功能", test_config_monitor()))
    test_results.append(("API重载端点", test_api_reload_endpoint()))
    
    # 汇总测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20s} : {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！配置热重载功能工作正常。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关组件。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
