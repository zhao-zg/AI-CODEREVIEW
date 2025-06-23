#!/usr/bin/env python3
"""
版本追踪管理工具
Version Tracking Management Tool
"""

import argparse
import sys
import os
from datetime import datetime
from tabulate import tabulate

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biz.utils.version_tracker import VersionTracker
from biz.service.review_service import ReviewService


def show_statistics():
    """显示版本追踪统计信息"""
    print("📊 版本追踪统计信息")
    print("=" * 50)
    
    stats = VersionTracker.get_version_statistics()
    
    print(f"🔢 总版本数: {stats['total_versions']}")
    print(f"📁 项目数: {stats['total_projects']}")
    print(f"📅 最近7天审查数: {stats['recent_reviews']}")
    print()
    
    if stats['project_stats']:
        print("📈 项目审查统计 (TOP 10):")
        headers = ["项目名称", "版本数量"]
        table_data = [(proj['project'], proj['count']) for proj in stats['project_stats']]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    else:
        print("📊 暂无项目统计数据")


def list_versions(project_name=None, limit=20):
    """列出已审查的版本"""
    print(f"📋 已审查版本列表 {'(项目: ' + project_name + ')' if project_name else ''}")
    print("=" * 80)
    
    versions = VersionTracker.get_reviewed_versions(project_name, limit)
    
    if not versions:
        print("🔍 没有找到已审查的版本")
        return
    
    headers = ["项目", "作者", "分支", "评分", "审查时间", "版本哈希"]
    table_data = []
    
    for version in versions:
        reviewed_at = datetime.fromtimestamp(version['reviewed_at']).strftime('%Y-%m-%d %H:%M')
        version_hash = version['version_hash'][:8] + "..."
        
        table_data.append([
            version['project_name'],
            version['author'][:15] if version['author'] else 'N/A',
            version['branch'][:20] if version['branch'] else 'N/A',
            f"{version['score']}分" if version['score'] else 'N/A',
            reviewed_at,
            version_hash
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\n显示了 {len(versions)} 条记录")


def show_version_details(version_hash):
    """显示版本详细信息"""
    print(f"🔍 版本详细信息 (哈希: {version_hash})")
    print("=" * 80)
    
    versions = VersionTracker.get_reviewed_versions(limit=1000)
    
    # 查找匹配的版本
    matched_version = None
    for version in versions:
        if version['version_hash'].startswith(version_hash):
            matched_version = version
            break
    
    if not matched_version:
        print(f"❌ 未找到哈希以 '{version_hash}' 开头的版本")
        return
    
    print(f"📁 项目名称: {matched_version['project_name']}")
    print(f"👤 作者: {matched_version['author']}")
    print(f"🌿 分支: {matched_version['branch']}")
    print(f"📊 评分: {matched_version['score']}分")
    print(f"🔗 提交SHA: {matched_version['commit_sha']}")
    print(f"📅 审查时间: {datetime.fromtimestamp(matched_version['reviewed_at']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 审查类型: {matched_version['review_type']}")
    print(f"🆔 版本哈希: {matched_version['version_hash']}")
    
    if matched_version['file_paths']:
        try:
            import json
            file_paths = json.loads(matched_version['file_paths'])
            print(f"📄 涉及文件 ({len(file_paths)}):")
            for path in file_paths[:10]:  # 只显示前10个文件
                print(f"   • {path}")
            if len(file_paths) > 10:
                print(f"   ... 还有 {len(file_paths) - 10} 个文件")
        except:
            print(f"📄 涉及文件: {matched_version['file_paths']}")
    
    print("\n📝 审查结果:")
    print("-" * 40)
    print(matched_version['review_result'])


def cleanup_old_records(days=30, dry_run=False):
    """清理旧记录"""
    print(f"🧹 清理 {days} 天前的版本记录")
    print("=" * 50)
    
    if dry_run:
        print("🔍 干跑模式 - 不会实际删除数据")
        # 这里可以添加预览逻辑
        print("实际清理请使用: --cleanup-days <天数>")
        return
    
    deleted_count = VersionTracker.cleanup_old_records(days)
    
    if deleted_count > 0:
        print(f"✅ 成功清理了 {deleted_count} 条旧记录")
    else:
        print("✨ 没有需要清理的记录")


def check_duplicate_versions():
    """检查重复版本"""
    print("🔍 检查重复版本...")
    print("=" * 50)
    
    # 获取所有版本
    versions = VersionTracker.get_reviewed_versions(limit=10000)
    
    # 按版本哈希分组
    hash_groups = {}
    for version in versions:
        version_hash = version['version_hash']
        if version_hash not in hash_groups:
            hash_groups[version_hash] = []
        hash_groups[version_hash].append(version)
    
    # 查找重复
    duplicates = {k: v for k, v in hash_groups.items() if len(v) > 1}
    
    if not duplicates:
        print("✅ 没有发现重复版本")
        return
    
    print(f"⚠️ 发现 {len(duplicates)} 个重复版本:")
    
    for version_hash, versions_list in duplicates.items():
        print(f"\n🔗 版本哈希: {version_hash[:16]}...")
        print(f"   重复次数: {len(versions_list)}")
        for i, version in enumerate(versions_list, 1):
            reviewed_at = datetime.fromtimestamp(version['reviewed_at']).strftime('%Y-%m-%d %H:%M')
            print(f"   {i}. {version['project_name']} - {version['author']} - {reviewed_at}")


def main():
    parser = argparse.ArgumentParser(description='版本追踪管理工具')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--list', action='store_true', help='列出已审查版本')
    parser.add_argument('--project', type=str, help='指定项目名称')
    parser.add_argument('--limit', type=int, default=20, help='限制显示数量')
    parser.add_argument('--details', type=str, help='显示版本详细信息（指定版本哈希前缀）')
    parser.add_argument('--cleanup-days', type=int, help='清理多少天前的记录')
    parser.add_argument('--cleanup-preview', action='store_true', help='预览清理操作')
    parser.add_argument('--check-duplicates', action='store_true', help='检查重复版本')
    
    args = parser.parse_args()
    
    # 确保数据库已初始化
    try:
        ReviewService.init_db()
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return 1
    
    try:
        if args.stats:
            show_statistics()
        elif args.list:
            list_versions(args.project, args.limit)
        elif args.details:
            show_version_details(args.details)
        elif args.cleanup_days:
            cleanup_old_records(args.cleanup_days)
        elif args.cleanup_preview:
            cleanup_old_records(30, dry_run=True)
        elif args.check_duplicates:
            check_duplicate_versions()
        else:
            print("🤖 AI代码审查系统 - 版本追踪管理工具")
            print()
            print("可用命令:")
            print("  --stats              显示统计信息")
            print("  --list               列出已审查版本")
            print("  --project <name>     指定项目名称")
            print("  --limit <number>     限制显示数量")
            print("  --details <hash>     显示版本详细信息")
            print("  --cleanup-days <n>   清理n天前的记录")
            print("  --cleanup-preview    预览清理操作")
            print("  --check-duplicates   检查重复版本")
            print()
            print("示例:")
            print("  python version_manager.py --stats")
            print("  python version_manager.py --list --project my-project --limit 10")
            print("  python version_manager.py --details abc123")
            print("  python version_manager.py --cleanup-days 30")
    
    except KeyboardInterrupt:
        print("\n🔴 操作被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
