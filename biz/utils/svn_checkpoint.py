#!/usr/bin/env python3
"""
SVN增量检查机制
记录每个仓库的上次检查时间，只处理新的提交
"""

import sqlite3
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 获取日志器
logger = logging.getLogger(__name__)

class SVNCheckpointManager:
    """SVN检查点管理器"""
    
    DB_FILE = "data/data.db"
    
    @staticmethod
    def init_db():
        """初始化检查点表"""
        try:
            with sqlite3.connect(SVNCheckpointManager.DB_FILE) as conn:
                cursor = conn.cursor()
                
                # 检查表是否已存在
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='svn_checkpoints'
                ''')
                table_exists = cursor.fetchone() is not None
                
                # 创建检查点表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS svn_checkpoints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        repo_name TEXT UNIQUE NOT NULL,
                        last_check_time INTEGER NOT NULL,
                        last_revision TEXT,
                        updated_at INTEGER NOT NULL,
                        created_at INTEGER NOT NULL
                    )
                ''')
                
                conn.commit()
                
                # 只在第一次创建表时打印消息
                if not table_exists:
                    logger.info("SVN检查点表初始化成功")
                
        except sqlite3.DatabaseError as e:
            logger.error(f"SVN检查点表初始化失败: {e}")
    
    @staticmethod
    def get_last_check_time(repo_name: str) -> int:
        """
        获取仓库的上次检查时间
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            上次检查的时间戳，如果没有记录则返回24小时前
        """
        try:
            with sqlite3.connect(SVNCheckpointManager.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT last_check_time FROM svn_checkpoints
                    WHERE repo_name = ?
                ''', (repo_name,))
                
                result = cursor.fetchone()
                if result:
                    return result[0]
                else:
                    # 首次检查，返回24小时前
                    return int(time.time() - 24 * 3600)
                    
        except sqlite3.DatabaseError as e:
            print(f"获取检查点失败: {e}")
            return int(time.time() - 24 * 3600)
    
    @staticmethod
    def update_checkpoint(repo_name: str, last_revision: str = None):
        """
        更新仓库的检查点
        
        Args:
            repo_name: 仓库名称
            last_revision: 最后处理的revision
        """
        try:
            current_time = int(time.time())
            
            with sqlite3.connect(SVNCheckpointManager.DB_FILE) as conn:
                cursor = conn.cursor()
                
                # 使用UPSERT操作
                cursor.execute('''
                    INSERT INTO svn_checkpoints 
                    (repo_name, last_check_time, last_revision, updated_at, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(repo_name) 
                    DO UPDATE SET 
                        last_check_time=excluded.last_check_time,
                        last_revision=excluded.last_revision,
                        updated_at=excluded.updated_at
                ''', (repo_name, current_time, last_revision, current_time, current_time))
                
                conn.commit()
                print(f"更新检查点成功: {repo_name} -> {datetime.fromtimestamp(current_time)}")
                
        except sqlite3.DatabaseError as e:
            print(f"更新检查点失败: {e}")
    
    @staticmethod
    def get_all_checkpoints():
        """获取所有检查点信息"""
        try:
            with sqlite3.connect(SVNCheckpointManager.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT repo_name, last_check_time, last_revision, updated_at
                    FROM svn_checkpoints
                    ORDER BY updated_at DESC
                ''')
                
                results = cursor.fetchall()
                checkpoints = []
                
                for row in results:
                    checkpoints.append({
                        'repo_name': row[0],
                        'last_check_time': row[1],
                        'last_check_time_str': datetime.fromtimestamp(row[1]).strftime('%Y-%m-%d %H:%M:%S'),
                        'last_revision': row[2],
                        'updated_at': row[3]
                    })
                
                return checkpoints
                
        except sqlite3.DatabaseError as e:
            print(f"获取检查点列表失败: {e}")
            return []

def test_checkpoint_manager():
    """测试检查点管理器"""
    print("=== 测试SVN检查点管理器 ===")
    
    # 初始化数据库
    SVNCheckpointManager.init_db()
    
    # 测试仓库
    test_repo = "test_repo"
    
    # 获取初始检查时间
    initial_time = SVNCheckpointManager.get_last_check_time(test_repo)
    print(f"初始检查时间: {datetime.fromtimestamp(initial_time)}")
    
    # 更新检查点
    SVNCheckpointManager.update_checkpoint(test_repo, "r12345")
    
    # 获取更新后的检查时间
    updated_time = SVNCheckpointManager.get_last_check_time(test_repo)
    print(f"更新后检查时间: {datetime.fromtimestamp(updated_time)}")
    
    # 验证时间更新
    if updated_time > initial_time:
        print("✅ 检查点更新成功")
    else:
        print("❌ 检查点更新失败")
    
    # 显示所有检查点
    checkpoints = SVNCheckpointManager.get_all_checkpoints()
    print(f"\n所有检查点 ({len(checkpoints)} 个):")
    for cp in checkpoints:
        print(f"  {cp['repo_name']}: {cp['last_check_time_str']} (r{cp['last_revision'] or 'unknown'})")
    
    return True

if __name__ == "__main__":
    test_checkpoint_manager()
