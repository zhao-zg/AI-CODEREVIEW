#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试0.45阈值的检测逻辑
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("conf/.env")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('.'))

from biz.svn.svn_worker import is_merge_commit_enhanced

def debug_threshold():
    """详细调试阈值检测逻辑"""
    print("🔍 详细调试增强Merge检测阈值逻辑")
    print("=" * 60)
    
    # 获取当前配置
    threshold = os.getenv('MERGE_DETECTION_THRESHOLD', '0.4')
    print(f"配置阈值: {threshold} (类型: {type(threshold)})")
    print(f"转换后: {float(threshold)} (类型: {type(float(threshold))})")
    print()
    
    # 测试边界情况
    test_commit = {
        'revision': '12348',
        'message': 'r12340 integration from branches/feature-x',
        'author': 'jenkins',
        'date': '2024-01-15 03:00:00',
        'paths': [{'path': f'/trunk/lib/module{i}.py', 'action': 'M'} for i in range(15)]
    }
    
    result = is_merge_commit_enhanced(test_commit)
    
    print("测试提交详情:")
    print(f"  消息: {test_commit['message']}")
    print(f"  作者: {test_commit['author']}")
    print(f"  文件数: {len(test_commit['paths'])}")
    print()
    
    print("检测结果详情:")
    print(f"  置信度: {result['confidence']} (类型: {type(result['confidence'])})")
    print(f"  是否merge: {result['is_merge']}")
    print(f"  检测方法: {result.get('detection_methods', [])}")
    print()
    
    print("证据详情:")
    for category, evidence in result.get('evidence', {}).items():
        print(f"  {category}: {evidence}")
    print()
    
    # 手动比较
    config_threshold = float(threshold)
    actual_confidence = result['confidence']
    print("阈值比较:")
    print(f"  配置阈值: {config_threshold}")
    print(f"  实际置信度: {actual_confidence}")
    print(f"  {actual_confidence} >= {config_threshold} = {actual_confidence >= config_threshold}")
    print(f"  差值: {actual_confidence - config_threshold}")
    
    # 测试不同的精度
    print("\n精度测试:")
    for test_threshold in [0.44, 0.45, 0.46]:
        meets_threshold = actual_confidence >= test_threshold
        print(f"  阈值 {test_threshold}: {meets_threshold}")

if __name__ == '__main__':
    debug_threshold()
