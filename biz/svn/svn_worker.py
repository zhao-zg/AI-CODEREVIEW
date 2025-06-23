import os
import json
import traceback
from datetime import datetime
from typing import List, Dict

from biz.entity.review_entity import SvnReviewEntity
from biz.event.event_manager import event_manager
from biz.svn.svn_handler import SVNHandler, filter_svn_changes
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.im import notifier
from biz.utils.log import logger
# === 版本追踪集成 ===
from biz.utils.version_tracker import VersionTracker
# === 版本追踪集成 END ===


def handle_multiple_svn_repositories(repositories_config: str = None, check_hours: int = None, check_limit: int = 100):
    """
    处理多个SVN仓库的变更
    :param repositories_config: SVN仓库配置JSON字符串，如果为None则从环境变量读取
    :param check_hours: 检查最近多少小时的变更，如果为None则使用各仓库的配置
    """
    try:
        # 解析仓库配置
        if repositories_config is None:
            repositories_config = os.environ.get('SVN_REPOSITORIES', '[]')
        
        try:
            repositories = json.loads(repositories_config)
        except json.JSONDecodeError as e:
            logger.error(f"SVN仓库配置JSON解析失败: {e}")
            return
        
        if not repositories:
            logger.info("没有配置SVN仓库")
            return
        
        logger.info(f"开始检查 {len(repositories)} 个SVN仓库")
        
        # 处理每个仓库
        for repo_config in repositories:
            try:
                repo_name = repo_config.get('name', 'unknown')
                remote_url = repo_config.get('remote_url')
                local_path = repo_config.get('local_path')
                username = repo_config.get('username')
                password = repo_config.get('password')
                repo_check_hours = check_hours or repo_config.get('check_hours', 24)
                
                if not remote_url or not local_path:
                    logger.error(f"仓库 {repo_name} 配置不完整，跳过")
                    continue
                
                logger.info(f"开始检查仓库: {repo_name}")
                handle_svn_changes(remote_url, local_path, username, password, repo_check_hours, check_limit, repo_name)
                
            except Exception as e:
                error_message = f'处理仓库 {repo_config.get("name", "unknown")} 时出现错误: {str(e)}\n{traceback.format_exc()}'
                logger.error(error_message)
                notifier.send_notification(content=error_message)
                
    except Exception as e:
        error_message = f'多仓库SVN变更检测出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('多仓库SVN变更检测出现未知错误: %s', error_message)


def handle_svn_changes(svn_remote_url: str, svn_local_path: str, svn_username: str = None, svn_password: str = None, check_hours: int = 24, check_limit: int = 100, repo_name: str = None):
    """
    处理SVN变更事件
    :param svn_remote_url: SVN远程仓库URL
    :param svn_local_path: SVN本地路径
    :param svn_username: SVN用户名
    :param svn_password: SVN密码    :param check_hours: 检查最近多少小时的变更
    :param check_limit: 限制检查的提交数量
    :param repo_name: 仓库名称
    """
    try:
        display_name = repo_name or os.path.basename(svn_local_path)
        logger.info(f'开始检查SVN变更，仓库: {display_name}，远程URL: {svn_remote_url}')
        
        # 创建SVN处理器
        svn_handler = SVNHandler(svn_remote_url, svn_local_path, svn_username, svn_password)
        
        # 更新工作副本
        if not svn_handler.update_working_copy():
            logger.error(f'仓库 {display_name} SVN工作副本更新失败')
            return
          # 获取最近的提交
        recent_commits = svn_handler.get_recent_commits(hours=check_hours, limit=check_limit)
        
        if not recent_commits:
            logger.info(f'仓库 {display_name} 没有发现最近的SVN提交')
            return
        
        logger.info(f'仓库 {display_name} 发现 {len(recent_commits)} 个最近的提交')
        
        # 处理每个提交
        for commit in recent_commits:
            process_svn_commit(svn_handler, commit, svn_local_path, display_name)
            
    except Exception as e:
        display_name = repo_name or os.path.basename(svn_local_path)
        error_message = f'仓库 {display_name} SVN变更检测出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('SVN变更检测出现未知错误: %s', error_message)


def process_svn_commit(svn_handler: SVNHandler, commit: Dict, svn_path: str, repo_name: str = None):
    """
    处理单个SVN提交
    :param svn_handler: SVN处理器
    :param commit: 提交信息
    :param svn_path: SVN路径
    :param repo_name: 仓库名称
    """
    try:
        revision = commit['revision']
        author = commit['author']
        message = commit['message']
        
        logger.info(f'处理SVN提交: r{revision} by {author}')
        
        # 获取提交的变更
        changes = svn_handler.get_commit_changes(commit)
        logger.info(f'变更文件数: {len(changes)}')
        
        # 过滤变更
        changes = filter_svn_changes(changes)
        
        if not changes:
            logger.info(f'提交 r{revision} 没有包含需要审查的文件类型')
            return
              # 统计新增和删除的代码行数
        additions = sum(change.get('additions', 0) for change in changes)
        deletions = sum(change.get('deletions', 0) for change in changes)
        
        # 获取项目名称
        project_name = repo_name or os.path.basename(svn_path.rstrip('/\\'))
        
        # 构造提交信息
        commit_info = [{
            'revision': revision,
            'message': message,
            'author': author,
            'date': commit['date']
        }]
        
        # === 版本追踪集成 - 检查是否已审查 ===
        version_tracking_enabled = os.environ.get('VERSION_TRACKING_ENABLED', '1') == '1'
        if version_tracking_enabled:
            # 检查该revision是否已审查
            existing_review = VersionTracker.is_version_reviewed(project_name, commit_info, changes)
            if existing_review:
                logger.info(f'SVN版本 r{revision} 已审查，跳过重复审查。')
                return
        # === 版本追踪集成 END ===
        
        # 进行代码审查
        review_result = "未进行代码审查"
        score = 0
        
        svn_review_enabled = os.environ.get('SVN_REVIEW_ENABLED', '1') == '1'
        
        if svn_review_enabled and changes:
            # 构造变更文本
            changes_text = ""
            for change in changes:
                changes_text += f"\n--- 文件: {change['new_path']} ---\n"
                changes_text += change['diff']
                changes_text += "\n"
            
            # 进行代码审查
            commits_text = f"SVN提交 r{revision}: {message}"
            review_result = CodeReviewer().review_and_strip_code(changes_text, commits_text)
            score = CodeReviewer.parse_review_score(review_text=review_result)
            logger.info(f'代码审查完成，评分: {score}')
          
        # 获取项目名称
        project_name = repo_name or os.path.basename(svn_path.rstrip('/\\'))
        
        # 构造提交信息
        commit_info = [{
            'revision': revision,
            'message': message,
            'author': author,
            'date': commit['date']
        }]
        
        # 触发事件
        event_manager['svn_reviewed'].send(SvnReviewEntity(
            project_name=project_name,
            author=author,
            revision=revision,
            updated_at=int(datetime.now().timestamp()),
            commits=commit_info,
            score=score,
            review_result=review_result,
            svn_path=svn_path,
            additions=additions,
            deletions=deletions,
        ))
        
        # 发送通知
        if svn_review_enabled and review_result != "未进行代码审查":
            notification_content = f"""
## SVN代码审查结果

**项目**: {project_name}
**版本**: r{revision}
**作者**: {author}
**提交信息**: {message}
**新增行数**: {additions}
**删除行数**: {deletions}
**评分**: {score}分

### 审查结果:
{review_result}
"""
            notifier.send_notification(
                content=notification_content, 
                msg_type="markdown", 
                title=f"SVN代码审查 - {project_name} r{revision}"
            )
        
        # 代码审查完成后，记录版本
        if version_tracking_enabled:
            VersionTracker.record_version_review(
                project_name=project_name,
                commits=commit_info,
                changes=changes,
                author=author,
                branch='',
                review_type='svn',
                review_result=review_result,
                score=score
            )
            logger.info(f'SVN版本 r{revision} 审查结果已记录到版本追踪。')
        
    except Exception as e:
        error_message = f'处理SVN提交 r{commit.get("revision", "unknown")} 时出现错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('处理SVN提交时出现错误: %s', error_message)
