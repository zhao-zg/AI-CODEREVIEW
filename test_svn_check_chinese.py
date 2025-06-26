#!/usr/bin/env python3
"""
测试 /svn/check 接口的中文输出
"""
import requests
import json
import sys

def test_svn_check_chinese_output():
    """测试 SVN 检查接口的中文输出"""
    print("🧪 测试 SVN 检查接口中文输出...")
    
    # 测试 URL
    base_url = "http://127.0.0.1:5001"
    
    try:
        # 测试基本 SVN 检查
        print("\n📋 测试: POST /svn/check")
        response = requests.post(f"{base_url}/svn/check", timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头 Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"响应原始内容: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                message = data.get('message', '')
                print(f"解析后的消息: {message}")
                print(f"消息长度: {len(message)}")
                print(f"消息字节: {message.encode('utf-8')}")
                
                # 检查是否包含中文
                chinese_chars = [char for char in message if '\u4e00' <= char <= '\u9fff']
                print(f"包含中文字符: {len(chinese_chars)} 个")
                if chinese_chars:
                    print(f"中文字符: {''.join(chinese_chars[:10])}")
                
            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {e}")
                print(f"原始响应: {repr(response.text)}")
        else:
            print(f"请求失败: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        print("请确保 API 服务正在运行: python api.py")
    except requests.exceptions.Timeout:
        print("⏰ 请求超时")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_svn_check_chinese_output()
