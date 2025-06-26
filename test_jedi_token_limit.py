#!/usr/bin/env python3
"""
测试 Jedi 客户端的 token 限制逻辑
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from biz.llm.client.jedi import JediClient
from biz.utils.default_config import get_env_int

def test_jedi_token_limits():
    """测试 Jedi 的 token 限制逻辑"""
    print("=== Jedi Token 限制测试 ===\n")
    
    # 模拟不同的 REVIEW_MAX_TOKENS 设置
    test_cases = [
        {"REVIEW_MAX_TOKENS": "5000", "description": "系统限制 5000 tokens"},
        {"REVIEW_MAX_TOKENS": "15000", "description": "系统限制 15000 tokens"},
        {"REVIEW_MAX_TOKENS": "25000", "description": "系统限制 25000 tokens"},
    ]
    
    for case in test_cases:
        print(f"🧪 测试场景: {case['description']}")
        
        # 设置环境变量
        os.environ["REVIEW_MAX_TOKENS"] = case["REVIEW_MAX_TOKENS"]
        system_max = get_env_int("REVIEW_MAX_TOKENS", 10000)
        print(f"   系统最大 tokens: {system_max}")
        
        # 模拟不同复杂度的请求
        test_messages = [
            {"content": "short message", "length": 100},  # 简单请求
            {"content": "medium length message" * 50, "length": 1000},  # 中等请求  
            {"content": "long complex message" * 200, "length": 3000},  # 复杂请求
        ]
        
        for msg in test_messages:
            mock_messages = [{"content": msg["content"]}]
            content_length = msg["length"]
            
            # 模拟 Jedi 的逻辑
            if content_length < 500:
                jedi_preference = 4000
                complexity = "simple"
            elif content_length < 2000:
                jedi_preference = 10000
                complexity = "medium"
            else:
                jedi_preference = 20000
                complexity = "complex"
            
            actual_tokens = min(jedi_preference, system_max)
            
            print(f"   {complexity:8} 请求 (长度:{content_length:4}): Jedi偏好={jedi_preference:5}, 实际使用={actual_tokens:5}")
        
        print()

if __name__ == "__main__":
    test_jedi_token_limits()
