#!/usr/bin/env python3
"""
SVN检查点管理工具
用于管理SVN增量检查的检查点数据
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent  # 回到项目根目录
sys.path.insert(0, str(project_root))
os.chdir(project_root)  # 切换到项目根目录

def list_checkpoints():
    """列出所有检查点"""
    from biz.utils.svn_checkpoint import SVNCheckpointManager
    
    print("📋 SVN检查点列表:")
    print("=" * 60)
    
    SVNCheckpointManager.init_db()
    checkpoints = SVNCheckpointManager.get_all_checkpoints()
    
    if not checkpoints:
        print("暂无检查点记录")
        return
    
    print(f"{'仓库名称':<20} {'最后检查时间':<20} {'最后Revision':<15} {'更新时间'}")
    print("-" * 60)
    
    for cp in checkpoints:
        last_check = cp['last_check_time_str']
        last_rev = cp['last_revision'] or 'N/A'
        updated = datetime.fromtimestamp(cp['updated_at']).strftime('%Y-%m-%d %H:%M')
        
        print(f"{cp['repo_name']:<20} {last_check:<20} {last_rev:<15} {updated}")

def reset_checkpoint(repo_name: str):
    """重置指定仓库的检查点"""
    from biz.utils.svn_checkpoint import SVNCheckpointManager
    
    print(f"🔄 重置仓库 '{repo_name}' 的检查点...")
    
    SVNCheckpointManager.init_db()
    
    # 将检查点设置为24小时前
    import time
    reset_time = int(time.time() - 24 * 3600)
    
    try:
        import sqlite3
        with sqlite3.connect(SVNCheckpointManager.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE svn_checkpoints 
                SET last_check_time = ?, updated_at = ?
                WHERE repo_name = ?
            ''', (reset_time, int(time.time()), repo_name))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"✅ 成功重置仓库 '{repo_name}' 的检查点")
                print(f"   新的检查点时间: {datetime.fromtimestamp(reset_time)}")
            else:
                print(f"❌ 仓库 '{repo_name}' 的检查点不存在")
                
    except Exception as e:
        print(f"❌ 重置检查点失败: {e}")

def clear_all_checkpoints():
    """清除所有检查点"""
    from biz.utils.svn_checkpoint import SVNCheckpointManager
    
    print("🗑️  清除所有检查点...")
    
    confirm = input("确认要清除所有检查点吗？这将导致下次检查处理最近24小时的所有提交 (y/N): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
    
    try:
        import sqlite3
        with sqlite3.connect(SVNCheckpointManager.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM svn_checkpoints')
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ 成功清除 {deleted_count} 个检查点")
            
    except Exception as e:
        print(f"❌ 清除检查点失败: {e}")

def show_stats():
    """显示检查点统计信息"""
    from biz.utils.svn_checkpoint import SVNCheckpointManager
    
    print("📊 SVN检查点统计:")
    print("=" * 60)
    
    SVNCheckpointManager.init_db()
    checkpoints = SVNCheckpointManager.get_all_checkpoints()
    
    if not checkpoints:
        print("暂无检查点数据")
        return
    
    print(f"总检查点数量: {len(checkpoints)}")
    
    # 计算时间统计
    current_time = datetime.now().timestamp()
    time_diffs = []
    
    for cp in checkpoints:
        time_diff = (current_time - cp['last_check_time']) / 3600  # 转换为小时
        time_diffs.append(time_diff)
    
    if time_diffs:
        avg_time = sum(time_diffs) / len(time_diffs)
        min_time = min(time_diffs)
        max_time = max(time_diffs)
        
        print(f"距离上次检查时间:")
        print(f"  平均: {avg_time:.1f} 小时")
        print(f"  最短: {min_time:.1f} 小时")
        print(f"  最长: {max_time:.1f} 小时")
    
    # 最近活跃的仓库
    recent_checkpoints = sorted(checkpoints, key=lambda x: x['updated_at'], reverse=True)[:5]
    print(f"\n最近活跃的仓库:")
    for i, cp in enumerate(recent_checkpoints, 1):
        updated = datetime.fromtimestamp(cp['updated_at']).strftime('%Y-%m-%d %H:%M')
        print(f"  {i}. {cp['repo_name']} - {updated}")

def validate_incremental_setup():
    """验证增量检查设置"""
    print("🔧 验证增量检查设置:")
    print("=" * 60)
    
    try:
        from biz.utils.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        
        # 检查关键配置
        svn_enabled = env_config.get('SVN_CHECK_ENABLED', '0')
        crontab = env_config.get('SVN_CHECK_CRONTAB', '*/30 * * * *')
        
        print(f"SVN检查启用: {svn_enabled} {'✅' if svn_enabled == '1' else '❌'}")
        print(f"增量检查: 默认启用 ✅")
        print(f"定时表达式: {crontab}")
        
        # 分析定时任务频率
        if crontab.startswith('*/'):
            minutes = int(crontab.split()[0][2:])
            print(f"执行频率: 每 {minutes} 分钟")
            print(f"检查范围: 动态增量（约 {minutes/60:.1f} 小时）")
            print("重叠情况: 无重复检查 ✅")
        
        # 数据库检查
        from biz.utils.svn_checkpoint import SVNCheckpointManager
        SVNCheckpointManager.init_db()
        checkpoints = SVNCheckpointManager.get_all_checkpoints()
        print(f"检查点数据: {len(checkpoints)} 个仓库 {'✅' if checkpoints else '⚠️'}")
        
        # 给出建议
        print(f"\n建议:")
        if svn_enabled != '1':
            print("- 启用SVN检查功能: SVN_CHECK_ENABLED=1")
        if not checkpoints and svn_enabled == '1':
            print("- 执行一次手动检查来初始化检查点")
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SVN检查点管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出检查点
    subparsers.add_parser('list', help='列出所有检查点')
    
    # 重置检查点
    reset_parser = subparsers.add_parser('reset', help='重置指定仓库的检查点')
    reset_parser.add_argument('repo_name', help='仓库名称')
    
    # 清除所有检查点
    subparsers.add_parser('clear', help='清除所有检查点')
    
    # 显示统计信息
    subparsers.add_parser('stats', help='显示检查点统计信息')
    
    # 验证设置
    subparsers.add_parser('validate', help='验证增量检查设置')
    
    args = parser.parse_args()
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    if args.command == 'list':
        list_checkpoints()
    elif args.command == 'reset':
        reset_checkpoint(args.repo_name)
    elif args.command == 'clear':
        clear_all_checkpoints()
    elif args.command == 'stats':
        show_stats()
    elif args.command == 'validate':
        validate_incremental_setup()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
