import sqlite3
import hashlib
import json
from typing import Optional, List, Dict
from datetime import datetime
from biz.utils.log import logger


class VersionTracker:
    """
    版本追踪器 - 用于记录已审查过的代码版本，避免重复审查
    """
    DB_FILE = "data/data.db"
    
    @staticmethod
    def init_db():
        """初始化版本追踪表"""
        try:
            with sqlite3.connect(VersionTracker.DB_FILE) as conn:
                cursor = conn.cursor()
                
                # 创建版本追踪表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS version_tracker (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_name TEXT NOT NULL,
                        version_hash TEXT NOT NULL,
                        commit_sha TEXT,
                        author TEXT,
                        branch TEXT,
                        file_paths TEXT,
                        changes_hash TEXT,
                        review_type TEXT,
                        reviewed_at INTEGER,
                        review_result TEXT,
                        score INTEGER,
                        created_at INTEGER,
                        UNIQUE(project_name, version_hash)
                    )
                ''')
                
                # 创建索引以提高查询性能
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_project_version 
                    ON version_tracker(project_name, version_hash)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_commit_sha 
                    ON version_tracker(commit_sha)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_changes_hash 
                    ON version_tracker(changes_hash)
                ''')
                
                conn.commit()
                logger.info("Version tracker database initialized successfully")
                
        except sqlite3.DatabaseError as e:
            logger.error(f"Version tracker database initialization failed: {e}")

    @staticmethod
    def generate_version_hash(commits: List[Dict], changes: List[Dict] = None) -> str:
        """
        生成版本哈希值，用于标识唯一的代码版本
        
        Args:
            commits: 提交信息列表
            changes: 变更信息列表（可选）
            
        Returns:
            版本哈希值
        """
        try:            # 提取关键信息用于生成哈希
            version_info = {
                'commits': [
                    {
                        'id': commit.get('id', commit.get('revision', '')),
                        'message': commit.get('message', ''),
                        'timestamp': commit.get('timestamp', commit.get('date', '')),
                        'author_email': commit.get('author', {}).get('email', '') if isinstance(commit.get('author'), dict) else commit.get('author', '')
                    }
                    for commit in commits
                ],
                'changes_count': len(changes) if changes else 0
            }
            
            # 如果有变更信息，添加文件路径和内容哈希
            if changes:
                version_info['file_paths'] = sorted([
                    change.get('new_path', '') for change in changes
                ])
                # 对变更内容生成哈希
                changes_content = ''.join([
                    change.get('diff', '') for change in changes
                ])
                version_info['changes_hash'] = hashlib.md5(
                    changes_content.encode('utf-8')
                ).hexdigest()
            
            # 生成版本哈希
            version_json = json.dumps(version_info, sort_keys=True, ensure_ascii=False)
            version_hash = hashlib.sha256(version_json.encode('utf-8')).hexdigest()
            
            return version_hash
            
        except Exception as e:
            logger.error(f"Error generating version hash: {e}")
            return ""

    @staticmethod
    def is_version_reviewed(project_name: str, commits: List[Dict], 
                          changes: List[Dict] = None) -> Optional[Dict]:
        """
        检查指定版本是否已经被审查过
        
        Args:
            project_name: 项目名称
            commits: 提交信息列表
            changes: 变更信息列表（可选）
            
        Returns:
            如果已审查过，返回审查信息字典；否则返回None
        """
        try:
            version_hash = VersionTracker.generate_version_hash(commits, changes)
            if not version_hash:
                return None
                
            with sqlite3.connect(VersionTracker.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM version_tracker 
                    WHERE project_name = ? AND version_hash = ?
                    ORDER BY reviewed_at DESC
                    LIMIT 1
                ''', (project_name, version_hash))
                
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    review_info = dict(zip(columns, result))                    
                    logger.info(f"Found existing review for project {project_name}, "
                              f"version {version_hash[:8]}...")
                    return review_info
                    
                return None
                
        except Exception as e:
            logger.error(f"Error checking version review status: {e}")
            return None

    @staticmethod
    def record_version_review(project_name: str, commits: List[Dict], 
                            changes: List[Dict] = None, author: str = "",
                            branch: str = "", review_type: str = "gitlab",
                            review_result: str = "", score: int = 0,
                            commit_message: str = "", commit_date: str = "",
                            additions_count: int = 0, deletions_count: int = 0) -> bool:
        """
        记录版本审查信息
        
        Args:
            project_name: 项目名称
            commits: 提交信息列表
            changes: 变更信息列表（可选）
            author: 作者
            branch: 分支
            review_type: 审查类型（gitlab/github/svn）
            review_result: 审查结果
            score: 审查评分
            commit_message: 提交消息
            commit_date: 提交日期
            additions_count: 新增行数
            deletions_count: 删除行数
            
        Returns:
            是否记录成功
        """
        try:
            version_hash = VersionTracker.generate_version_hash(commits, changes)
            if not version_hash:
                return False
                
            # 生成变更哈希
            changes_hash = ""
            file_paths = ""
            file_details = ""
            
            if changes:
                changes_content = ''.join([change.get('diff', '') for change in changes])
                changes_hash = hashlib.md5(changes_content.encode('utf-8')).hexdigest()
                file_paths = json.dumps([change.get('new_path', '') for change in changes])
                
                # 构建文件详细信息
                files_info = []
                for change in changes:
                    file_info = {
                        'path': change.get('full_path', change.get('new_path', '')),
                        'name': change.get('new_path', ''),
                        'action': change.get('action', 'M'),
                        'additions': change.get('additions', 0),
                        'deletions': change.get('deletions', 0),
                        'diff_preview': change.get('diff', '')[:200] + '...' if len(change.get('diff', '')) > 200 else change.get('diff', '')
                    }
                    files_info.append(file_info)
                
                file_details = json.dumps({
                    'files': files_info,
                    'summary': {
                        'total_files': len(files_info),
                        'total_additions': sum(f['additions'] for f in files_info),
                        'total_deletions': sum(f['deletions'] for f in files_info)
                    }
                }, ensure_ascii=False)
            
            # 获取第一个commit的SHA和相关信息
            commit_sha = commits[0].get('id', commits[0].get('revision', '')) if commits else ""
            if not commit_message and commits:
                commit_message = commits[0].get('message', '')
            if not commit_date and commits:
                commit_date = commits[0].get('date', '')
            
            current_time = int(datetime.now().timestamp())
            
            with sqlite3.connect(VersionTracker.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO version_tracker 
                    (project_name, version_hash, commit_sha, author, branch, 
                     file_paths, changes_hash, review_type, reviewed_at, 
                     review_result, score, created_at, commit_message, commit_date,
                     additions_count, deletions_count, file_details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_name, version_hash, commit_sha, author, branch,
                    file_paths, changes_hash, review_type, current_time,
                    review_result, score, current_time, commit_message, commit_date,
                    additions_count, deletions_count, file_details
                ))
                
                conn.commit()
                logger.info(f"Recorded version review for project {project_name}, "
                          f"version {version_hash[:8]}... with detailed info")
                return True
                
        except Exception as e:
            logger.error(f"Error recording version review: {e}")
            return False

    @staticmethod
    def get_reviewed_versions(project_name: str = None, limit: int = 100) -> List[Dict]:
        """
        获取已审查的版本列表
        
        Args:
            project_name: 项目名称（可选）
            limit: 返回数量限制
            
        Returns:
            已审查版本列表
        """
        try:
            with sqlite3.connect(VersionTracker.DB_FILE) as conn:
                cursor = conn.cursor()
                
                if project_name:
                    cursor.execute('''
                        SELECT * FROM version_tracker 
                        WHERE project_name = ?
                        ORDER BY reviewed_at DESC
                        LIMIT ?
                    ''', (project_name, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM version_tracker 
                        ORDER BY reviewed_at DESC
                        LIMIT ?
                    ''', (limit,))
                
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                return [dict(zip(columns, result)) for result in results]
                
        except Exception as e:
            logger.error(f"Error getting reviewed versions: {e}")
            return []

    @staticmethod
    def cleanup_old_records(days: int = 30) -> int:
        """
        清理旧的审查记录
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数
        """
        try:
            cutoff_time = int((datetime.now().timestamp() - (days * 24 * 3600)))
            
            with sqlite3.connect(VersionTracker.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM version_tracker 
                    WHERE created_at < ?
                ''', (cutoff_time,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old version records")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
            return 0

    @staticmethod
    def get_version_statistics() -> Dict:
        """
        获取版本追踪统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with sqlite3.connect(VersionTracker.DB_FILE) as conn:
                cursor = conn.cursor()
                
                # 总记录数
                cursor.execute('SELECT COUNT(*) FROM version_tracker')
                total_count = cursor.fetchone()[0]
                
                # 项目数量
                cursor.execute('SELECT COUNT(DISTINCT project_name) FROM version_tracker')
                project_count = cursor.fetchone()[0]
                
                # 最近7天的审查数量
                recent_time = int((datetime.now().timestamp() - (7 * 24 * 3600)))
                cursor.execute('SELECT COUNT(*) FROM version_tracker WHERE reviewed_at > ?', 
                             (recent_time,))
                recent_count = cursor.fetchone()[0]
                
                # 按项目分组统计
                cursor.execute('''
                    SELECT project_name, COUNT(*) as count 
                    FROM version_tracker 
                    GROUP BY project_name 
                    ORDER BY count DESC
                    LIMIT 10
                ''')
                project_stats = cursor.fetchall()
                
                return {
                    'total_versions': total_count,
                    'total_projects': project_count,
                    'recent_reviews': recent_count,
                    'project_stats': [
                        {'project': row[0], 'count': row[1]} 
                        for row in project_stats
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting version statistics: {e}")
            return {
                'total_versions': 0,
                'total_projects': 0,
                'recent_reviews': 0,
                'project_stats': []
            }
