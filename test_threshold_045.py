#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试增强merge检测的0.45阈值效果
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("conf/.env")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('.'))

from biz.svn.svn_worker import is_merge_commit_enhanced

def test_threshold_045():
    """测试0.45阈值下的检测效果"""
    print("🧪 测试增强Merge检测 - 阈值0.45")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            'name': '明确的merge消息',
            'commit': {
                'revision': '12345',
                'message': 'Merged /branches/feature-auth into /trunk',
                'author': 'developer',
                'date': '2024-01-15 15:30:00',
                'paths': [
                    {'path': '/trunk/src/auth.py', 'action': 'M'},
                    {'path': '/trunk/src/login.py', 'action': 'M'},
                    {'path': '/trunk/tests/test_auth.py', 'action': 'A'},
                ]
            },
            'expected': True
        },
        {
            'name': '隐式大型merge',
            'commit': {
                'revision': '12348',
                'message': 'r12340 integration from branches/feature-x',
                'author': 'jenkins',
                'date': '2024-01-15 03:00:00',
                'paths': [{'path': f'/trunk/lib/module{i}.py', 'action': 'M'} for i in range(15)]
            },
            'expected': True
        },
        {
            'name': '同步更新',
            'commit': {
                'revision': '12349',
                'message': 'Sync latest changes',
                'author': 'developer',
                'date': '2024-01-15 16:00:00',
                'paths': [{'path': f'/trunk/src/module{i}.py', 'action': 'M'} for i in range(18)]
            },
            'expected': True
        },
        {
            'name': '普通bugfix',
            'commit': {
                'revision': '12350',
                'message': 'Fix payment bug',
                'author': 'developer',
                'date': '2024-01-15 11:00:00',
                'paths': [{'path': '/trunk/src/payment.py', 'action': 'M'}]
            },
            'expected': False
        }
    ]
    
    # 显示当前配置
    threshold = os.getenv('MERGE_DETECTION_THRESHOLD', '0.4')
    enabled = os.getenv('USE_ENHANCED_MERGE_DETECTION', '0') == '1'
    print(f"当前配置: 增强检测={enabled}, 阈值={threshold}")
    print()
    
    print("测试场景                置信度      检测结果    预期    状态")
    print("-" * 60)
    
    all_passed = True
    for case in test_cases:
        result = is_merge_commit_enhanced(case['commit'])
        confidence = result['confidence']
        detected = result['is_merge']
        expected = case['expected']
        status = "✅" if detected == expected else "❌"
        
        if detected != expected:
            all_passed = False
        
        print(f"{case['name']:<20} {confidence:<10.2f} {'是' if detected else '否':<8} {'是' if expected else '否':<6} {status}")
    
    print()
    if all_passed:
        print("🎉 所有测试通过！阈值0.45工作正常")
    else:
        print("⚠️ 部分测试未通过，需要调整阈值")
    
    return all_passed

if __name__ == '__main__':
    test_threshold_045()
