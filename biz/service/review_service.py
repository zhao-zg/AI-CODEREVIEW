import sqlite3
import json
import re
from typing import Optional

import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity, SvnReviewEntity
from biz.utils.log import logger


def _extract_svn_line_from_paths(paths_text: str) -> str:
    """从 SVN 文件路径文本（version_tracker.file_paths，JSON 数组字符串）提取 SVN 线。

    file_paths 形如 '["/trunk/config/item.xlsx", "/branches/dev/code.py"]'（仓库根相对路径），
    线 = 第一个路径段（trunk）或前两段（branches/分支名、tags/标签名），slug 化后返回
    （branches/dev-1.0 → branches_dev_1_0）。提取不到返回空串，调用方回退默认 Webhook。
    """
    try:
        paths = json.loads(paths_text) if paths_text else []
    except (ValueError, TypeError):
        paths = []
    for path in paths or []:
        parts = str(path or '').strip('/').split('/')
        if not parts or not parts[0]:
            continue
        if parts[0] in ('trunk', 'branches', 'tags'):
            if parts[0] in ('branches', 'tags') and len(parts) >= 2 and parts[1]:
                line = f"{parts[0]}_{parts[1]}"
            else:
                line = parts[0]
            return re.sub(r'[^A-Za-z0-9]+', '_', line).strip('_') or ''
    return ''


def _retry_svn_excel_review(project_name: str, revision: str, diff_struct: dict,
                            file_paths: str, commit_message: str) -> tuple:
    """SVN 重新AI评审的 Excel 专用链路（与首次审查保持一致）。

    首次审查时 Excel 走专用链路：svn cat 原始字节 → parse_workbook → excel_review_prompt，
    但 version_tracker.file_details 里 Excel 条目的 diff 为空字符串（二进制文件没有文本 diff，
    见 svn_worker._extract_excel_changes 注释）。若重试时把空 diff 直接交给通用 CodeReviewer，
    AI 只看到 .xlsx 文件名而看不到任何表格内容，会误报
    "由于 .xlsx 是二进制格式，无法进行有效的差异审查和内容验证"。

    本函数按 project_name 从 SVN_REPOSITORIES 匹配仓库配置，重建 SVNHandler 重新读取
    新旧版本内容，复用 svn_worker._review_excel_changes 走与首次审查一致的 Excel 链路。

    :return: (excel_report, excel_score, code_struct)
        - excel_report 为 None：无 Excel 文件或无法走 Excel 链路（EXCEL_REVIEW_ENABLED=0 /
          缺仓库配置 / 异常），调用方应全部按代码审查处理；
        - code_struct 为 None：无代码文件（纯 Excel 提交），报告直接取 Excel 结果；
        - 否则 code_struct 为剔除 Excel 文件后的剩余 diff（供混合提交的代码审查，
          避免 AI 再看到二进制的空 diff）。
    """
    from biz.utils.config_manager import ConfigManager
    from biz.svn.svn_handler import SVNHandler
    from biz.svn.svn_worker import _review_excel_changes

    try:
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        if not str(env_config.get('EXCEL_REVIEW_ENABLED', '1')).lower() in ('1', 'true', 'yes', 'on'):
            return None, None, diff_struct
        excel_exts = tuple(
            ext.strip().lower()
            for ext in env_config.get('EXCEL_SUPPORTED_EXTENSIONS', '.xlsx,.xls,.csv').split(',')
            if ext.strip()
        )
        if not excel_exts:
            return None, None, diff_struct

        # 1. 收集 Excel 文件路径与 action（优先 file_details.files，兜底 file_paths）
        excel_changes = []
        excel_paths = set()
        for finfo in diff_struct.get('files', []):
            fp = finfo.get('path', '')
            if fp and fp.lower().endswith(excel_exts):
                excel_paths.add(fp)
                excel_changes.append({'file_path': fp, 'action': finfo.get('action', 'M')})
        if not excel_paths and file_paths:
            try:
                for fp in json.loads(file_paths):
                    if str(fp).lower().endswith(excel_exts):
                        excel_paths.add(str(fp))
                        excel_changes.append({'file_path': str(fp), 'action': 'M'})
            except (ValueError, TypeError):
                pass
        if not excel_changes:
            return None, None, diff_struct

        # 2. 按 project_name 匹配仓库配置（name 或 local_path 的 basename）
        repo_conf = _find_svn_repo_config(project_name, env_config)
        if not repo_conf:
            logger.warning(f'重新AI评审: 未找到项目 {project_name} 的 SVN 仓库配置，'
                           f'无法执行 Excel 配置表审查，回退代码审查')
            return None, None, diff_struct
        assert repo_conf is not None

        # 3. 重建 SVNHandler，走与首次审查一致的 Excel 专用链路
        # 注：str(x or '') 包装以消除 Optional 类型报错；空串在 SVNHandler 的
        # `if self.svn_username and self.svn_password` 判断中等同 None，不会加认证参数。
        svn_handler = SVNHandler(
            str(repo_conf.get('remote_url') or ''),
            str(repo_conf.get('local_path') or ''),
            str(repo_conf.get('username') or ''),
            str(repo_conf.get('password') or ''),
        )
        report, score = _review_excel_changes(
            svn_handler, excel_changes, revision, commits_text=commit_message or '',
        )
        if not report or not report.strip():
            logger.warning(f'重新AI评审: Excel 配置表审查返回空结果，回退代码审查: {revision}')
            return None, None, diff_struct

        # 4. 剔除 Excel 文件后的剩余代码 diff（供混合提交的代码审查）
        code_files = [f for f in diff_struct.get('files', [])
                      if f.get('path', '') not in excel_paths]
        code_struct = None
        if code_files:
            code_struct = {
                'files': code_files,
                'summary': diff_struct.get('summary', {}),
            }
        return report, score, code_struct
    except Exception as e:
        logger.error(f'重新AI评审 Excel 配置表审查失败: {type(e).__name__}: {e}')
        return None, None, diff_struct


def _find_svn_repo_config(project_name: str, env_config: dict) -> Optional[dict]:
    """按 project_name 从 SVN_REPOSITORIES 匹配仓库配置（name 或 local_path 的 basename）。"""
    import os
    try:
        repositories = json.loads(env_config.get('SVN_REPOSITORIES', '[]'))
    except (ValueError, TypeError):
        return None
    for r in repositories:
        if r.get('name') == project_name or \
                os.path.basename(str(r.get('local_path', ''))) == project_name:
            return r
    return None


def _retry_svn_code_review(project_name: str, revision: str, diff_struct: dict,
                           commit_message: str) -> tuple:
    """SVN 重新AI评审的代码审查链路（与首次审查保持一致：Agentic 或分批审查）。

    version_tracker.file_details 里只存了 diff_preview（≤200 字符预览），Agentic 模式下
    AI 可用 read_file 工具从服务器读取完整文件内容，正好弥补预览截断的缺陷。

    :return: (result, score)；result 为空时按"代码审查返回空结果"处理
    """
    from biz.utils.config_manager import ConfigManager
    from biz.utils.code_reviewer import BatchCodeReviewer, CodeReviewer, is_api_error_message

    files_json = []
    for f in diff_struct.get('files', []):
        files_json.append({
            'file_path': f.get('path', f.get('name', '')),
            'status': f.get('action', 'M'),
            'diff': f.get('diff') or f.get('diff_preview', ''),
            'additions': f.get('additions', 0),
            'deletions': f.get('deletions', 0),
        })
    if not files_json:
        return "代码审查返回空结果", 0

    try:
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        agentic = str(env_config.get('AGENTIC_REVIEW_ENABLED', '0')).lower() in ('1', 'true', 'yes', 'on')
    except Exception:
        agentic = False
        env_config = {}

    if agentic:
        repo_conf = _find_svn_repo_config(project_name, env_config)
        if repo_conf:
            assert repo_conf is not None
            try:
                from biz.svn.svn_handler import SVNHandler
                from biz.utils.agentic_reviewer import AgenticCodeReviewer
                # str(x or '') 包装以消除 Optional 类型报错；空串在 SVNHandler 的
                # `if self.svn_username and self.svn_password` 判断中等同 None。
                svn_handler = SVNHandler(
                    str(repo_conf.get('remote_url') or ''),
                    str(repo_conf.get('local_path') or ''),
                    str(repo_conf.get('username') or ''),
                    str(repo_conf.get('password') or ''),
                )
                tool_context = {
                    'read_file': lambda file_path: svn_handler.read_working_copy_file(
                        file_path, revision=revision
                    ),
                    'search_code': svn_handler.search_working_copy,
                }
                result = AgenticCodeReviewer(tool_context=tool_context).review_in_batches(
                    files_json, commit_message or ''
                )
                if result and result.strip() and not is_api_error_message(result):
                    return result, CodeReviewer.parse_review_score(result)
                logger.warning(f'重新AI评审 Agentic 代码审查结果异常，降级普通审查: '
                               f'{(result or "")[:100]}')
            except Exception as e:
                logger.error(f'重新AI评审 Agentic 代码审查失败，降级普通审查: '
                             f'{type(e).__name__}: {e}')
        else:
            logger.warning(f'重新AI评审: 未找到项目 {project_name} 的 SVN 仓库配置，'
                           f'Agentic 代码审查降级为普通分批审查')

    # 普通（非 Agentic，或 Agentic 降级）
    result = BatchCodeReviewer().review_in_batches(files_json, commit_message or '')
    if result and result.strip():
        if is_api_error_message(result):
            return result, 0
        return result, CodeReviewer.parse_review_score(result)
    return "代码审查返回空结果", 0


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
                    ''')
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS svn_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            revision TEXT,
                            svn_path TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0,
                            file_details TEXT,
                            trigger_type TEXT DEFAULT 'scheduled'
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
    def insert_svn_review_log(entity: SvnReviewEntity):
        """插入SVN审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO svn_review_log (project_name, author, revision, svn_path, updated_at, commit_messages, score, review_result, additions, deletions, trigger_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                               (entity.project_name, entity.author, entity.revision,
                                entity.svn_path, entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions, entity.trigger_type))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting svn review log: {e}")

    @staticmethod
    def insert_svn_review_log_with_details(entity: SvnReviewEntity, file_details=None):
        """插入SVN审核日志，支持结构化diff存储"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO svn_review_log (project_name, author, revision, svn_path, updated_at, commit_messages, score, review_result, additions, deletions, file_details, trigger_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                               (entity.project_name, entity.author, entity.revision,
                                entity.svn_path, entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions, file_details, entity.trigger_type))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting svn review log: {e}")

    @staticmethod
    def get_svn_review_logs(authors: list = None, project_names: list = None, revisions: list = None,
                             updated_at_gte: int = None, updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的SVN审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                query = """
                    SELECT project_name, author, revision, svn_path, updated_at, commit_messages, score, review_result, additions, deletions, trigger_type
                    FROM svn_review_log
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
                if revisions:
                    placeholders = ','.join(['?'] * len(revisions))
                    query += f" AND revision IN ({placeholders})"
                    params.extend(revisions)
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
            print(f"Error retrieving svn review logs: {e}")
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
            start_date: 开始日期 (datetime/date/str)
            end_date: 结束日期 (datetime/date/str)
            authors: 作者列表
            projects: 项目列表
            score_range: 分数范围 [min, max]
        
        Returns:
            dict: 包含success状态和data数据的字典
        """
        from datetime import datetime as dt, date as d
        
        def _to_timestamp(val):
            """将日期值转换为Unix时间戳"""
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, dt):
                return int(val.timestamp())
            if isinstance(val, d):
                return int(dt.combine(val, dt.min.time()).timestamp())
            if isinstance(val, str):
                try:
                    return int(dt.strptime(val, '%Y-%m-%d').timestamp())
                except ValueError:
                    return None
            return None
        
        try:
            data = []            
            if review_type == 'mr' or review_type is None:
                # 获取MR审查记录
                mr_logs_df = ReviewService.get_mr_review_logs(
                    authors=authors,
                    project_names=projects,
                    updated_at_gte=_to_timestamp(start_date),
                    updated_at_lte=_to_timestamp(end_date)
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
                    updated_at_gte=_to_timestamp(start_date),
                    updated_at_lte=_to_timestamp(end_date)
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
                    updated_at_gte=_to_timestamp(start_date),
                    updated_at_lte=_to_timestamp(end_date),
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
        异步执行，完成后推送通知
        :param review_type: 审查类型
        :param identifier: 唯一标识（如id/commit_sha/version_hash）
        :return: 提交结果确认
        """
        from biz.utils.queue import handle_queue
        
        # 使用队列异步执行重新审查
        handle_queue(ReviewService._async_retry_review, review_type, identifier)
        
        return {
            "success": True, 
            "message": f"重新AI评审任务已提交，将在后台异步执行并推送通知",
            "review_type": review_type,
            "identifier": identifier
        }

    @staticmethod
    def _async_retry_review(review_type, identifier):
        """
        异步执行重新AI评审的内部方法
        """
        # 确保在后台进程中加载环境配置
        try:
            from dotenv import load_dotenv
            load_dotenv("conf/.env")
        except ImportError:
            logger.warning("dotenv 模块未安装，使用系统环境变量")
        except Exception as e:
            logger.warning(f"加载 .env 文件失败: {e}")
        
        from biz.utils.code_reviewer import CodeReviewer
        from biz.event.event_manager import on_merge_request_reviewed, on_push_reviewed, on_svn_reviewed
        import json
        import time
        
        try:
            conn = sqlite3.connect(ReviewService.DB_FILE)
            cursor = conn.cursor()
            
            if review_type == 'mr':
                cursor.execute("SELECT * FROM mr_review_log WHERE id=?", (identifier,))
                row = cursor.fetchone()
                if not row:
                    logger.error(f"未找到MR审查记录: {identifier}")
                    return
                
                # 解构数据库字段 (13个字段)
                (id_, project_name, author, source_branch, target_branch, updated_at, 
                 commit_messages, score, url, review_result, additions, deletions, file_details) = row
                
                if not file_details:
                    logger.error(f"MR记录 {identifier} 未存储结构化diff，无法重新AI审查")
                    return
                
                # 执行AI审查
                diff_struct = json.loads(file_details)
                new_review_result = CodeReviewer().review_and_strip_code(
                    json.dumps(diff_struct, ensure_ascii=False), commit_messages
                )
                new_score = CodeReviewer.parse_review_score(new_review_result)
                reviewed_at = int(time.time())
                
                # 更新数据库
                cursor.execute(
                    "UPDATE mr_review_log SET review_result=?, score=?, updated_at=? WHERE id=?", 
                    (new_review_result, new_score, reviewed_at, id_)
                )
                conn.commit()
                
                # 触发推送通知
                try:
                    mr_entity = MergeRequestReviewEntity(
                        project_name=project_name,
                        author=author,
                        source_branch=source_branch,
                        target_branch=target_branch,
                        updated_at=reviewed_at,
                        commits=[{"message": commit_messages}],
                        score=float(new_score),
                        url=url or "http://localhost/mr/unknown",
                        review_result=new_review_result,
                        url_slug="retry_review",
                        webhook_data={},
                        additions=additions or 0,
                        deletions=deletions or 0,
                        mr_id=int(id_)
                    )
                    on_merge_request_reviewed(mr_entity)
                    logger.info(f"MR {identifier} 重新AI评审完成并已推送通知")
                except Exception as e:
                    logger.error(f"MR {identifier} 推送通知失败: {e}")
                
            elif review_type == 'push':
                cursor.execute("SELECT * FROM push_review_log WHERE id=?", (identifier,))
                row = cursor.fetchone()
                if not row:
                    logger.error(f"未找到Push审查记录: {identifier}")
                    return
                
                # 解构数据库字段 (11个字段)
                (id_, project_name, author, branch, updated_at, commit_messages, 
                 score, review_result, additions, deletions, file_details) = row
                
                if not file_details:
                    logger.error(f"Push记录 {identifier} 未存储结构化diff，无法重新AI审查")
                    return
                
                # 执行AI审查
                diff_struct = json.loads(file_details)
                new_review_result = CodeReviewer().review_and_strip_code(
                    json.dumps(diff_struct, ensure_ascii=False), commit_messages
                )
                new_score = CodeReviewer.parse_review_score(new_review_result)
                reviewed_at = int(time.time())
                
                # 更新数据库
                cursor.execute(
                    "UPDATE push_review_log SET review_result=?, score=?, updated_at=? WHERE id=?", 
                    (new_review_result, new_score, reviewed_at, id_)
                )
                conn.commit()
                
                # 触发推送通知
                try:
                    commits_list = json.loads(commit_messages) if commit_messages.startswith('[') else [{"message": commit_messages}]
                    
                    push_entity = PushReviewEntity(
                        project_name=project_name,
                        author=author,
                        branch=branch,
                        updated_at=reviewed_at,
                        commits=commits_list,
                        score=float(new_score),
                        review_result=new_review_result,
                        url_slug="retry_review",
                        webhook_data={"ref": f"refs/heads/{branch}"},
                        additions=additions or 0,
                        deletions=deletions or 0
                    )
                    on_push_reviewed(push_entity)
                    logger.info(f"Push {identifier} 重新AI评审完成并已推送通知")
                except Exception as e:
                    logger.error(f"Push {identifier} 推送通知失败: {e}")
                
            elif review_type in ['svn', 'github']:
                cursor.execute("SELECT * FROM version_tracker WHERE version_hash=? OR commit_sha=? OR rowid=?", 
                              (identifier, identifier, identifier))
                row = cursor.fetchone()
                if not row:
                    logger.error(f"未找到版本追踪审查记录: {identifier}")
                    return
                
                # 解构数据库字段 (18个字段)
                (id_, project_name, version_hash, commit_sha, author, branch, file_paths, changes_hash,
                 review_type_db, reviewed_at, review_result, score, created_at, commit_message, 
                 commit_date, additions_count, deletions_count, file_details) = row
                
                # 执行AI审查
                try:
                    diff_struct = json.loads(file_details) if file_details else {}
                except Exception:
                    diff_struct = {}
                
                # === 重新AI评审：代码与 Excel 均与首次审查走同一链路（Agentic/分批/Excel专用） ===
                # 首次审查时：代码走 BatchCodeReviewer / AgenticCodeReviewer（AGENTIC_REVIEW_ENABLED
                # 开启时 AI 可调 read_file/search_code 工具），Excel 走 svn cat 原始字节 →
                # parse_workbook → excel_review_prompt。但 version_tracker.file_details 里
                # Excel 条目 diff 为空（二进制文件无文本 diff）、代码条目只存了 diff_preview 预览；
                # 若重试时把这些残缺输入直接交给通用 CodeReviewer，AI 看不到内容会误报
                # "由于 .xlsx 是二进制格式，无法进行有效的差异审查和内容验证"。
                # 此处重建 SVNHandler，代码/Excel 各走专用链路；Agentic 模式 AI 仍可读取
                # 服务器上该 revision 的完整文件内容，正好弥补 diff_preview 截断的缺陷。
                use_svn_retry = review_type_db == 'svn' and commit_sha and commit_sha.isdigit()
                excel_report = None
                excel_score = 0
                code_struct = diff_struct
                if use_svn_retry:
                    excel_report, excel_score, code_struct = _retry_svn_excel_review(
                        project_name, commit_sha, diff_struct, file_paths, commit_message,
                    )

                if excel_report is not None and code_struct is not None:
                    # 混合提交：代码部分（Agentic/分批）+ Excel 部分分节合并，分数保持代码审查分数
                    code_result, code_score = _retry_svn_code_review(
                        project_name, commit_sha, code_struct, commit_message,
                    )
                    new_review_result = f"{code_result}\n\n---\n\n# 📊 Excel 配置表审查\n\n{excel_report}"
                    new_score = code_score
                elif excel_report is not None:
                    # 纯 Excel 配置表提交：报告与分数均取 Excel 审查结果
                    new_review_result = f"# 📊 Excel 配置表审查\n\n{excel_report}"
                    new_score = excel_score
                elif use_svn_retry:
                    # svn 纯代码提交（无 Excel），或 Excel 链路不可用时的回退
                    new_review_result, new_score = _retry_svn_code_review(
                        project_name, commit_sha, diff_struct, commit_message,
                    )
                else:
                    # github 类型 / 非数字 revision：维持原逻辑
                    new_review_result = CodeReviewer().review_and_strip_code(
                        json.dumps(diff_struct, ensure_ascii=False), commit_message
                    )
                    new_score = CodeReviewer.parse_review_score(new_review_result)
                # 重新审查不应影响时间点，保留原 reviewed_at
                # new_reviewed_at = int(time.time())
                # 更新数据库
                cursor.execute(
                    "UPDATE version_tracker SET review_result=?, score=? WHERE version_hash= ?",
                    (new_review_result, new_score, version_hash)
                )
                conn.commit()
                # 触发推送通知 (主要针对SVN)
                if review_type_db == 'svn':
                    try:
                        # 从文件路径中提取SVN版本号
                        svn_revision = commit_sha if commit_sha and commit_sha.isdigit() else "unknown"

                        # === 修复：详情页(show_svn_detail)是从 svn_review_log 表查询的，不是
                        # version_tracker。上面只更新了 version_tracker，svn_review_log 里的旧记录
                        # 不会变，而下面 on_svn_reviewed() 触发的是"新增一条记录"而不是"更新"，
                        # 导致同一 revision 下出现新旧两条记录，详情页按 revision 查询取到的还是
                        # 旧的那条——这就是"重新审查后网页内容还是老的"的根因。这里显式先把旧记录
                        # 原地更新掉，跟 mr/push 分支的做法保持一致。
                        if svn_revision != "unknown":
                            cursor.execute(
                                "UPDATE svn_review_log SET review_result=?, score=? WHERE revision=?",
                                (new_review_result, new_score, svn_revision)
                            )
                            conn.commit()
                        else:
                            logger.warning(f"SVN {identifier} 无法解析出有效revision，跳过更新 svn_review_log")

                        svn_entity = SvnReviewEntity(
                            project_name=project_name,
                            author=author,
                            revision=svn_revision,
                            updated_at=reviewed_at,
                            commits=[{"message": commit_message}],
                            score=float(new_score),
                            review_result=new_review_result,
                            svn_path=file_paths or f"/{project_name}",
                            additions=additions_count or 0,
                            deletions=deletions_count or 0,
                            branch=_extract_svn_line_from_paths(file_paths)
                        )
                        on_svn_reviewed(svn_entity)
                        logger.info(f"SVN {identifier} 重新AI评审完成并已推送通知")
                    except Exception as e:
                        logger.error(f"SVN {identifier} 推送通知失败: {e}")
                else:
                    logger.info(f"{review_type} {identifier} 重新AI评审完成 (无推送通知)")
                
            else:
                logger.error(f"暂不支持的重新审查类型: {review_type}")
                
        except Exception as e:
            logger.error(f"重新AI评审执行失败 {review_type} {identifier}: {e}")
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
