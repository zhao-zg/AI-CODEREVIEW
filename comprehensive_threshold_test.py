#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面验证0.45阈值效果的测试脚本
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("conf/.env")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('.'))

from biz.svn.svn_worker import is_merge_commit_enhanced, is_merge_commit

def comprehensive_threshold_test():
    """全面测试0.45阈值效果"""
    print("🧪 全面验证增强Merge检测 - 阈值0.45")
    print("=" * 80)
    
    # 显示当前配置
    threshold = os.getenv('MERGE_DETECTION_THRESHOLD', '0.4')
    enabled = os.getenv('USE_ENHANCED_MERGE_DETECTION', '0') == '1'
    print(f"📋 当前配置: 增强检测={enabled}, 阈值={threshold}")
    print()
    
    # 扩展测试用例
    test_cases = [
        {
            'name': '明确SVN merge',
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
            'name': '自动化CI merge',
            'commit': {
                'revision': '12346',
                'message': 'Auto merge r12340-12345',
                'author': 'buildbot',
                'date': '2024-01-15 02:00:00',
                'paths': [{'path': f'/trunk/src/file{i}.py', 'action': 'M'} for i in range(25)]
            },
            'expected': True
        },
        {
            'name': '边界情况：15文件修改',
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
            'name': '大型同步更新',
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
            'name': '中等规模修改',
            'commit': {
                'revision': '12350',
                'message': 'Update multiple modules',
                'author': 'developer',
                'date': '2024-01-15 14:00:00',
                'paths': [{'path': f'/trunk/src/mod{i}.py', 'action': 'M'} for i in range(8)]
            },
            'expected': False
        },
        {
            'name': '普通bug修复',
            'commit': {
                'revision': '12351',
                'message': 'Fix payment bug',
                'author': 'developer',
                'date': '2024-01-15 11:00:00',
                'paths': [{'path': '/trunk/src/payment.py', 'action': 'M'}]
            },
            'expected': False
        },
        {
            'name': '误导性文件名',
            'commit': {
                'revision': '12352',
                'message': 'Update merge sort algorithm',
                'author': 'developer',
                'date': '2024-01-15 14:00:00',
                'paths': [{'path': '/trunk/src/sort.py', 'action': 'M'}]
            },
            'expected': False
        },
        {
            'name': '小批量文档更新',
            'commit': {
                'revision': '12353',
                'message': 'Update documentation',
                'author': 'developer',
                'date': '2024-01-15 15:00:00',
                'paths': [
                    {'path': '/trunk/docs/api.md', 'action': 'M'},
                    {'path': '/trunk/README.md', 'action': 'M'},
                ]
            },
            'expected': False
        }
    ]
    
    print("🔍 详细测试结果:")
    print("=" * 80)
    print(f"{'序号':<4} {'测试场景':<20} {'传统':<6} {'增强':<6} {'置信度':<8} {'预期':<6} {'状态':<6} {'检测维度'}")
    print("-" * 80)
    
    all_passed = True
    high_confidence_count = 0
    medium_confidence_count = 0
    low_confidence_count = 0
    
    for i, case in enumerate(test_cases, 1):
        # 传统检测
        traditional_result = is_merge_commit(case['commit']['message'])
        
        # 增强检测
        enhanced_result = is_merge_commit_enhanced(case['commit'])
        
        confidence = enhanced_result['confidence']
        detected = enhanced_result['is_merge']
        expected = case['expected']
        
        # 统计置信度分布
        if confidence >= 0.7:
            high_confidence_count += 1
        elif confidence >= 0.4:
            medium_confidence_count += 1
        else:
            low_confidence_count += 1
        
        # 检查结果
        test_passed = detected == expected
        if not test_passed:
            all_passed = False
        
        # 格式化输出
        trad_icon = "✅" if traditional_result else "❌"
        enh_icon = "✅" if detected else "❌"
        conf_str = f"{confidence:.3f}"
        exp_icon = "✅" if expected else "❌"
        status_icon = "✅" if test_passed else "❌"
        methods = ', '.join(enhanced_result.get('detection_methods', []))
        
        print(f"{i:<4} {case['name']:<20} {trad_icon:<6} {enh_icon:<6} {conf_str:<8} {exp_icon:<6} {status_icon:<6} {methods}")
        
        # 显示详细证据（仅针对失败或边界情况）
        if not test_passed or abs(confidence - 0.45) < 0.01:
            print(f"     💡 证据: {enhanced_result.get('evidence', {})}")
    
    print("\n📊 测试统计:")
    print("=" * 80)
    print(f"总测试用例: {len(test_cases)}")
    print(f"通过用例: {sum(1 for case in test_cases if case['expected'] == is_merge_commit_enhanced(case['commit'])['is_merge'])}")
    print(f"传统检测准确率: {sum(1 for case in test_cases if case['expected'] == is_merge_commit(case['commit']['message'])) / len(test_cases) * 100:.1f}%")
    print(f"增强检测准确率: {sum(1 for case in test_cases if case['expected'] == is_merge_commit_enhanced(case['commit'])['is_merge']) / len(test_cases) * 100:.1f}%")
    
    print(f"\n🎯 置信度分布:")
    print(f"高置信度 (≥0.7): {high_confidence_count} 个")
    print(f"中等置信度 (0.4-0.7): {medium_confidence_count} 个")
    print(f"低置信度 (<0.4): {low_confidence_count} 个")
    
    print(f"\n🎉 测试结果: {'所有测试通过' if all_passed else '部分测试失败'}")
    
    if all_passed:
        print("✅ 0.45阈值表现优秀，推荐在生产环境使用")
    else:
        print("⚠️ 建议根据实际需求调整阈值")
    
    return all_passed

if __name__ == '__main__':
    comprehensive_threshold_test()
