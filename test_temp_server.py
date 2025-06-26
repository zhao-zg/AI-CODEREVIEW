#!/usr/bin/env python3
"""
测试临时服务器的中文输出
"""
import requests
import time

def test_temp_server():
    """测试临时服务器"""
    print("🧪 测试临时服务器中文输出...")
    
    # 等待服务器启动
    time.sleep(2)
    
    base_url = "http://127.0.0.1:5002"
    
    try:
        # 测试 SVN 端点
        print("\n📋 测试: POST /svn/check (临时服务器)")
        response = requests.post(f"{base_url}/svn/check", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {response.headers.get('content-type')}")
        print(f"原始响应: {response.text}")
        
        # 测试配置端点
        print("\n📋 测试: GET /test/config")
        response = requests.get(f"{base_url}/test/config", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"原始响应: {response.text}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_temp_server()
