#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SVN详细数据支持 - 数据库升级脚本
"""
import sqlite3
import os

def upgrade_version_tracker_table():
    """升级version_tracker表，添加详细数据支持字段"""
    DB_FILE = "data/data.db"
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # 检查现有表结构
            cursor.execute("PRAGMA table_info(version_tracker)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # 需要添加的新字段
            new_columns = [
                ("commit_message", "TEXT"),
                ("commit_date", "TEXT"),
                ("additions_count", "INTEGER DEFAULT 0"),
                ("deletions_count", "INTEGER DEFAULT 0"),
                ("file_details", "TEXT")  # JSON格式存储文件详细信息
            ]
            
            print("=== 当前表结构 ===")
            print(f"现有字段: {columns}")
            
            # 添加缺失的字段
            added_fields = []
            for column_name, column_type in new_columns:
                if column_name not in columns:
                    try:
                        sql = f"ALTER TABLE version_tracker ADD COLUMN {column_name} {column_type}"
                        cursor.execute(sql)
                        added_fields.append(column_name)
                        print(f"✅ 添加字段: {column_name} ({column_type})")
                    except sqlite3.Error as e:
                        print(f"❌ 添加字段失败 {column_name}: {e}")
                else:
                    print(f"⚪ 字段已存在: {column_name}")
            
            if added_fields:
                conn.commit()
                print(f"✅ 数据库升级完成，新增字段: {added_fields}")
            else:
                print("✅ 数据库结构已是最新，无需升级")
            
            # 验证升级结果
            cursor.execute("PRAGMA table_info(version_tracker)")
            new_columns_info = cursor.fetchall()
            print(f"\n升级后表结构:")
            for col in new_columns_info:
                print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULLABLE'}")
                
    except Exception as e:
        print(f"❌ 数据库升级失败: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("开始升级version_tracker表...")
    if upgrade_version_tracker_table():
        print("✅ 升级完成")
    else:
        print("❌ 升级失败")
