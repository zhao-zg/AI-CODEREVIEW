import sqlite3

import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity


class ReviewService:
    DB_FILE = "data/data.db"
    
    @staticmethod
    def init_db():
        """初始化数据库及表结构"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS mr_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            source_branch TEXT,
                            target_branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            url TEXT,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0
                        )
                    ''')
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS push_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0
                        )
                    ''')                # 确保旧版本的mr_review_log、push_review_log表添加additions、deletions列
                tables = ["mr_review_log", "push_review_log"]
                columns = ["additions", "deletions"]
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    current_columns = [col[1] for col in cursor.fetchall()]
                    for column in columns:
                        if column not in current_columns:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER DEFAULT 0")
                conn.commit()
                
            # 初始化版本追踪数据库
            from biz.utils.version_tracker import VersionTracker
            VersionTracker.init_db()
            
        except sqlite3.DatabaseError as e:
            print(f"Database initialization failed: {e}")

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO mr_review_log (project_name,author, source_branch, target_branch, updated_at, commit_messages, score, url,review_result, additions, deletions)
                                VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.source_branch,
                                entity.target_branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.url, entity.review_result, entity.additions, entity.deletions))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def insert_mr_review_log_with_details(entity: MergeRequestReviewEntity, file_details=None):
        """插入合并请求审核日志，支持结构化diff存储"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO mr_review_log (project_name,author, source_branch, target_branch, updated_at, commit_messages, score, url,review_result, additions, deletions, file_details)
                                VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.source_branch,
                                entity.target_branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.url, entity.review_result, entity.additions, entity.deletions, file_details))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def get_mr_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                           updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                query = """
                            SELECT project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions
                            FROM mr_review_log
                            WHERE 1=1
                            """
                params = []

                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)
                query += " ORDER BY updated_at DESC"
                df = pd.read_sql_query(sql=query, con=conn, params=params)
            return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def insert_push_review_log(entity: PushReviewEntity):
        """插入推送审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO push_review_log (project_name,author, branch, updated_at, commit_messages, score,review_result, additions, deletions)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def insert_push_review_log_with_details(entity: PushReviewEntity, file_details=None):
        """插入推送审核日志，支持结构化diff存储"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO push_review_log (project_name,author, branch, updated_at, commit_messages, score,review_result, additions, deletions, file_details)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions, file_details))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def get_push_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                             updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                # 基础查询
                query = """
                    SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions
                    FROM push_review_log
                    WHERE 1=1
                """
                params = []

                # 动态添加 authors 条件
                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                # 动态添加 updated_at_gte 条件
                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                # 动态添加 updated_at_lte 条件
                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)

                # 按 updated_at 降序排序
                query += " ORDER BY updated_at DESC"

                # 执行查询
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving push review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_version_tracking_logs(authors: list = None, project_names: list = None, 
                                 updated_at_gte: int = None, updated_at_lte: int = None,
                                 review_types: list = None) -> pd.DataFrame:
        """获取符合条件的版本跟踪审核日志（包括SVN、GitHub、GitLab）"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                # 基础查询
                query = """
                    SELECT project_name, author, branch, reviewed_at as updated_at, 
                           commit_message, review_result, score, review_type,
                           file_paths, commit_sha, version_hash, commit_date,
                           created_at, additions_count, deletions_count, file_details
                    FROM version_tracker
                    WHERE 1=1
                """
                params = []

                # 动态添加条件
                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND reviewed_at >= ?"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND reviewed_at <= ?"
                    params.append(updated_at_lte)
                
                if review_types:
                    placeholders = ','.join(['?'] * len(review_types))
                    query += f" AND review_type IN ({placeholders})"
                    params.extend(review_types)

                # 按时间降序排序
                query += " ORDER BY reviewed_at DESC"

                # 执行查询
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving version tracking logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_review_type_stats() -> dict:
        """获取不同审查类型的统计信息"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                
                # 统计各类型数量
                stats = {}
                
                # MR审查
                cursor.execute("SELECT COUNT(*) FROM mr_review_log")
                stats['mr_count'] = cursor.fetchone()[0]
                
                # Push审查
                cursor.execute("SELECT COUNT(*) FROM push_review_log")
                stats['push_count'] = cursor.fetchone()[0]
                
                # 版本跟踪审查（按类型分组）
                cursor.execute("""
                    SELECT review_type, COUNT(*) as count 
                    FROM version_tracker 
                    GROUP BY review_type
                """)
                version_stats = cursor.fetchall()
                for review_type, count in version_stats:
                    stats[f'{review_type}_count'] = count
                
                # 项目分布
                cursor.execute("""
                    SELECT project_name, review_type, COUNT(*) as count
                    FROM version_tracker
                    GROUP BY project_name, review_type
                    ORDER BY count DESC
                """)
                project_stats = cursor.fetchall()
                stats['project_distribution'] = [
                    {'project': row[0], 'type': row[1], 'count': row[2]}
                    for row in project_stats
                ]
                
                return stats
                
        except sqlite3.DatabaseError as e:
            print(f"Error getting review type stats: {e}")
            return {}

    @staticmethod
    def get_review_statistics(review_type=None, start_date=None, end_date=None, 
                            authors=None, projects=None, score_range=None):
        """
        获取审查统计数据
        
        Args:
            review_type: 审查类型 ('mr', 'push', 'svn', 'github')
            start_date: 开始日期
            end_date: 结束日期  
            authors: 作者列表
            projects: 项目列表
            score_range: 分数范围 [min, max]
        
        Returns:
            dict: 包含success状态和data数据的字典
        """
        try:
            data = []            
            if review_type == 'mr' or review_type is None:
                # 获取MR审查记录
                mr_logs_df = ReviewService.get_mr_review_logs(
                    authors=authors,
                    project_names=projects,
                    updated_at_gte=int(start_date.timestamp()) if start_date else None,
                    updated_at_lte=int(end_date.timestamp()) if end_date else None
                )
                for _, log in mr_logs_df.iterrows():
                    # 应用分数过滤
                    if score_range and (log['score'] < score_range[0] or log['score'] > score_range[1]):
                        continue
                        
                    data.append({
                        'type': 'mr',
                        'project': log['project_name'],
                        'author': log['author'],
                        'timestamp': log['updated_at'],
                        'score': log['score'],
                        'additions': log.get('additions', 0),
                        'deletions': log.get('deletions', 0),
                        'url': log.get('url', ''),
                        'branch_info': f"{log['source_branch']} → {log['target_branch']}",
                        'commit_messages': log['commit_messages'],
                        'review_result': log['review_result']
                    })
            
            if review_type == 'push' or review_type is None:
                # 获取Push审查记录
                push_logs_df = ReviewService.get_push_review_logs(
                    authors=authors,
                    project_names=projects,
                    updated_at_gte=int(start_date.timestamp()) if start_date else None,
                    updated_at_lte=int(end_date.timestamp()) if end_date else None
                )
                for _, log in push_logs_df.iterrows():
                    # 应用分数过滤
                    if score_range and (log['score'] < score_range[0] or log['score'] > score_range[1]):
                        continue
                        
                    data.append({
                        'type': 'push',
                        'project': log['project_name'],
                        'author': log['author'],
                        'timestamp': log['updated_at'],
                        'score': log['score'],
                        'additions': log.get('additions', 0),
                        'deletions': log.get('deletions', 0),
                        'branch_info': log['branch'],
                        'commit_messages': log['commit_messages'],
                        'review_result': log['review_result']
                    })            
            if review_type in ['svn', 'github'] or review_type is None:
                # 获取版本跟踪审查记录
                version_logs_df = ReviewService.get_version_tracking_logs(
                    authors=authors,
                    project_names=projects,
                    updated_at_gte=int(start_date.timestamp()) if start_date else None,
                    updated_at_lte=int(end_date.timestamp()) if end_date else None,
                    review_types=[review_type] if review_type else None
                )
                for _, log in version_logs_df.iterrows():
                    # 应用分数过滤
                    if score_range and (log['score'] < score_range[0] or log['score'] > score_range[1]):
                        continue
                        
                    data.append({
                        'type': log['review_type'],
                        'project': log['project_name'],
                        'author': log['author'],
                        'timestamp': log['updated_at'],
                        'score': log['score'],
                        'additions': log.get('additions_count', 0),
                        'deletions': log.get('deletions_count', 0),
                        'branch_info': log.get('branch', ''),
                        'commit_messages': log.get('commit_message', ''),
                        'review_result': log.get('review_result', ''),
                        'commit_sha': log.get('commit_sha', ''),
                        'commit_date': log.get('commit_date', ''),
                        'created_at': log.get('created_at', log.get('updated_at', 0)),
                        'file_details': log.get('file_details', ''),
                        'file_paths': log.get('file_paths', '')
                    })
            
            return {
                'success': True,
                'data': data,
                'total_count': len(data)
            }
            
        except Exception as e:
            print(f"Error getting review statistics: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }

    @staticmethod
    def retry_review(review_type, identifier):
        """
        管理员触发的重新AI评审逻辑，支持mr/push/svn/github等类型
        :param review_type: 审查类型
        :param identifier: 唯一标识（如id/commit_sha/version_hash）
        :return: 新的审查结果
        """
        from biz.utils.code_reviewer import CodeReviewer
        import json
        import time
        conn = sqlite3.connect(ReviewService.DB_FILE)
        try:
            cursor = conn.cursor()
            if review_type == 'mr':
                cursor.execute("SELECT id, commit_messages, file_details FROM mr_review_log WHERE id=?", (identifier,))
                row = cursor.fetchone()
                if not row:
                    return {"success": False, "message": "未找到MR审查记录"}
                id_, commit_messages, file_details = row
                if not file_details:
                    return {"success": False, "message": "该MR记录未存储结构化diff，无法重新AI审查"}
                diff_struct = json.loads(file_details)
                review_result = CodeReviewer().review_and_strip_code(json.dumps(diff_struct, ensure_ascii=False), commit_messages)
                score = CodeReviewer.parse_review_score(review_result)
                reviewed_at = int(time.time())
                cursor.execute("UPDATE mr_review_log SET review_result=?, score=?, updated_at=? WHERE id=?", (review_result, score, reviewed_at, id_))
                conn.commit()
                return {"success": True, "message": "MR重新AI审查完成", "review_result": review_result, "score": score}
            elif review_type == 'push':
                cursor.execute("SELECT id, commit_messages, file_details FROM push_review_log WHERE id=?", (identifier,))
                row = cursor.fetchone()
                if not row:
                    return {"success": False, "message": "未找到Push审查记录"}
                id_, commit_messages, file_details = row
                if not file_details:
                    return {"success": False, "message": "该Push记录未存储结构化diff，无法重新AI审查"}
                diff_struct = json.loads(file_details)
                review_result = CodeReviewer().review_and_strip_code(json.dumps(diff_struct, ensure_ascii=False), commit_messages)
                score = CodeReviewer.parse_review_score(review_result)
                reviewed_at = int(time.time())
                cursor.execute("UPDATE push_review_log SET review_result=?, score=?, updated_at=? WHERE id=?", (review_result, score, reviewed_at, id_))
                conn.commit()
                return {"success": True, "message": "Push重新AI审查完成", "review_result": review_result, "score": score}
            elif review_type in ['svn', 'github']:
                cursor.execute("SELECT * FROM version_tracker WHERE version_hash=? OR commit_sha=? OR rowid=?", (identifier, identifier, identifier))
                row = cursor.fetchone()
                if not row:
                    return {"success": False, "message": "未找到版本追踪审查记录"}
                project_name = row[1]
                author = row[2]
                branch = row[3]
                commit_message = row[4]
                review_type_db = row[7]
                file_details = row[14]
                file_paths = row[9]
                try:
                    diff_struct = json.loads(file_details) if file_details else {}
                except Exception:
                    diff_struct = {}
                commits_text = commit_message
                review_result = CodeReviewer().review_and_strip_code(json.dumps(diff_struct, ensure_ascii=False), commits_text)
                score = CodeReviewer.parse_review_score(review_result)
                reviewed_at = int(time.time())
                cursor.execute("UPDATE version_tracker SET review_result=?, score=?, reviewed_at=? WHERE version_hash=?", (review_result, score, reviewed_at, row[10]))
                conn.commit()
                return {"success": True, "message": "重新AI审查完成", "review_result": review_result, "score": score}
            else:
                return {"success": False, "message": f"暂不支持的类型: {review_type}"}
        finally:
            conn.close()

    @staticmethod
    def upgrade_db_add_file_details():
        """升级数据库，为mr_review_log和push_review_log表增加file_details字段"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                for table in ["mr_review_log", "push_review_log"]:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]
                    if "file_details" not in columns:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN file_details TEXT")
                conn.commit()
        except Exception as e:
            print(f"升级数据库添加file_details字段失败: {e}")

# Initialize database
ReviewService.init_db()
# 启动时自动升级
ReviewService.upgrade_db_add_file_details()
