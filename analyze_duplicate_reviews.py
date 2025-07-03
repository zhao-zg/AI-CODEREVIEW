#!/usr/bin/env python3
"""
修复SVN定时审查重复问题的解决方案
主要问题：
1. 时间窗口重叠导致重复检查
2. 版本哈希生成不稳定
3. 缺乏增量检查机制
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def analyze_duplicate_reviews():
    """分析重复审查问题"""
    print("=== 分析SVN重复审查问题 ===")
    
    try:
        from biz.utils.version_tracker import VersionTracker
        
        # 分析最近的审查记录
        versions = VersionTracker.get_reviewed_versions(limit=100)
        
        # 按项目分组
        projects = {}
        for version in versions:
            project_name = version['project_name']
            if project_name not in projects:
                projects[project_name] = []
            projects[project_name].append(version)
        
        print(f"发现 {len(projects)} 个项目的审查记录:")
        
        total_duplicates = 0
        for project_name, project_versions in projects.items():
            print(f"\n📁 项目: {project_name}")
            print(f"   总审查次数: {len(project_versions)}")
            
            # 按版本哈希分组
            hash_groups = {}
            revision_groups = {}
            
            for version in project_versions:
                version_hash = version['version_hash']
                commit_sha = version.get('commit_sha', '')
                
                # 按哈希分组
                if version_hash not in hash_groups:
                    hash_groups[version_hash] = []
                hash_groups[version_hash].append(version)
                
                # 按SVN revision分组
                if commit_sha:
                    if commit_sha not in revision_groups:
                        revision_groups[commit_sha] = []
                    revision_groups[commit_sha].append(version)
            
            # 检查重复
            hash_duplicates = {k: v for k, v in hash_groups.items() if len(v) > 1}
            revision_duplicates = {k: v for k, v in revision_groups.items() if len(v) > 1}
            
            if hash_duplicates:
                print(f"   ❌ 发现 {len(hash_duplicates)} 个版本哈希重复:")
                for version_hash, versions_list in hash_duplicates.items():
                    print(f"      哈希: {version_hash[:16]}... (重复 {len(versions_list)} 次)")
                    total_duplicates += len(versions_list) - 1
            
            if revision_duplicates:
                print(f"   ❌ 发现 {len(revision_duplicates)} 个SVN revision重复:")
                for revision, versions_list in revision_duplicates.items():
                    print(f"      r{revision} (重复 {len(versions_list)} 次)")
                    for i, version in enumerate(versions_list):
                        reviewed_at = datetime.fromtimestamp(version['reviewed_at']).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"         {i+1}. {reviewed_at} - 哈希: {version['version_hash'][:16]}...")
        
        print(f"\n📊 总计发现 {total_duplicates} 个重复审查")
        return total_duplicates > 0
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return False

def show_recent_svn_schedule():
    """显示最近的SVN检查调度情况"""
    print("\n=== SVN定时检查调度分析 ===")
    
    try:
        # 模拟显示定时任务配置
        from biz.utils.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        
        svn_crontab = env_config.get('SVN_CHECK_CRONTAB', '*/30 * * * *')
        svn_check_hours = env_config.get('SVN_CHECK_INTERVAL_HOURS', '24')
        
        print(f"定时表达式: {svn_crontab}")
        print(f"检查时间窗口: 最近 {svn_check_hours} 小时")
        
        # 计算定时任务频率
        if svn_crontab.startswith('*/'):
            minutes = int(svn_crontab.split()[0][2:])
            hours_window = int(svn_check_hours)
            overlap_ratio = (hours_window * 60) / minutes
            
            print(f"执行频率: 每 {minutes} 分钟")
            print(f"重叠倍数: {overlap_ratio:.1f} 倍")
            
            if overlap_ratio > 10:
                print("❌ 严重重叠: 每次检查都会重复处理大量历史提交")
                return True
            elif overlap_ratio > 2:
                print("⚠️  轻微重叠: 可能存在重复检查")
                return True
            else:
                print("✅ 时间窗口合理")
                return False
        
        return False
        
    except Exception as e:
        print(f"❌ 调度分析失败: {e}")
        return False

def test_version_hash_stability():
    """测试版本哈希生成的稳定性"""
    print("\n=== 版本哈希稳定性测试 ===")
    
    try:
        from biz.utils.version_tracker import VersionTracker
        
        # 模拟相同的SVN提交信息，测试哈希一致性
        test_commit = {
            'revision': '12345',
            'message': 'test commit',
            'author': 'testuser',
            'date': '2025-01-01 10:00:00'
        }
        
        test_changes = [
            {
                'new_path': 'test.py',
                'diff': '+print("hello")\n-print("old")'
            }
        ]
        
        # 生成多次哈希，检查一致性
        hashes = []
        for i in range(5):
            hash_value = VersionTracker.generate_version_hash([test_commit], test_changes)
            hashes.append(hash_value)
            print(f"第{i+1}次: {hash_value[:16]}...")
        
        # 检查一致性
        unique_hashes = set(hashes)
        if len(unique_hashes) == 1:
            print("✅ 版本哈希生成稳定")
            return True
        else:
            print(f"❌ 版本哈希不稳定，生成了 {len(unique_hashes)} 个不同的哈希")
            return False
        
    except Exception as e:
        print(f"❌ 哈希稳定性测试失败: {e}")
        return False

def propose_solutions():
    """提出解决方案"""
    print("\n=== 解决方案建议 ===")
    
    solutions = [
        {
            "name": "优化时间窗口策略",
            "description": "实现增量检查，只处理上次检查后的新提交",
            "priority": "高",
            "implementation": [
                "记录上次检查的时间戳",
                "使用上次检查时间作为起始点，而不是固定的小时数",
                "避免重复处理已检查的提交"
            ]
        },
        {
            "name": "优化版本哈希算法",
            "description": "简化哈希生成，提高稳定性",
            "priority": "中",
            "implementation": [
                "主要基于SVN revision生成哈希",
                "移除时间戳等易变因素",
                "确保相同revision总是生成相同哈希"
            ]
        },
        {
            "name": "增强重复检测",
            "description": "在SVN层面增加更强的重复检测",
            "priority": "中", 
            "implementation": [
                "检查revision是否已经审查过",
                "在版本追踪之外增加简单的revision缓存",
                "避免对相同revision进行版本哈希计算"
            ]
        },
        {
            "name": "调整定时任务配置",
            "description": "优化定时任务的执行频率和检查范围",
            "priority": "低",
            "implementation": [
                "减少检查频率或缩小时间窗口",
                "从每30分钟改为每小时或每2小时",
                "检查时间窗口从24小时改为1-2小时"
            ]
        }
    ]
    
    for i, solution in enumerate(solutions, 1):
        print(f"\n{i}. {solution['name']} (优先级: {solution['priority']})")
        print(f"   描述: {solution['description']}")
        print(f"   实现方式:")
        for impl in solution['implementation']:
            print(f"     - {impl}")
    
    return solutions

def main():
    """主函数"""
    print("开始分析SVN定时审查重复问题...")
    print("=" * 60)
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    # 分析问题
    has_duplicates = analyze_duplicate_reviews()
    has_overlap = show_recent_svn_schedule()
    hash_stable = test_version_hash_stability()
    
    # 提出解决方案
    solutions = propose_solutions()
    
    # 总结
    print("\n" + "=" * 60)
    print("问题诊断结果:")
    print("=" * 60)
    
    issues_found = []
    if has_duplicates:
        issues_found.append("❌ 发现重复审查记录")
    if has_overlap:
        issues_found.append("❌ 定时任务时间窗口重叠")
    if not hash_stable:
        issues_found.append("❌ 版本哈希生成不稳定")
    
    if issues_found:
        print("发现的问题:")
        for issue in issues_found:
            print(f"  {issue}")
        print(f"\n建议优先实施: {solutions[0]['name']}")
    else:
        print("✅ 未发现明显问题，系统运行正常")
    
    return len(issues_found) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
