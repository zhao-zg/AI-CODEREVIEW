#!/usr/bin/env python3
"""
对比测试两个端点的中文输出
"""
import requests
import json

def compare_endpoints():
    """对比两个端点的输出"""
    base_url = "http://127.0.0.1:5001"
    
    print("🔍 对比测试中文输出...")
    
    # 测试新的测试端点
    print("\n1️⃣ 测试端点: /test/chinese")
    try:
        response = requests.get(f"{base_url}/test/chinese", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"原始响应: {response.text}")
        if response.status_code == 200:
            data = response.json()
            print(f"配置检查: {data.get('config_check')}")
    except Exception as e:
        print(f"测试端点请求失败: {e}")
    
    # 测试原来的 SVN 端点
    print("\n2️⃣ SVN端点: /svn/check")
    try:
        response = requests.post(f"{base_url}/svn/check", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"原始响应: {response.text}")
    except Exception as e:
        print(f"SVN端点请求失败: {e}")

if __name__ == "__main__":
    compare_endpoints()
