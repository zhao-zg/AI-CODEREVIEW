import os
import traceback
from datetime import datetime

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.event.event_manager import event_manager
from biz.gitlab.webhook_handler import filter_changes, MergeRequestHandler, PushHandler
from biz.github.webhook_handler import filter_changes as filter_github_changes, PullRequestHandler as GithubPullRequestHandler, PushHandler as GithubPushHandler
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.version_tracker import VersionTracker
from biz.utils.default_config import get_env_bool



def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    push_review_enabled = get_env_bool('PUSH_REVIEW_ENABLED')
    # 检查是否启用版本追踪功能
    version_tracking_enabled = get_env_bool('VERSION_TRACKING_ENABLED')
    
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return
            
        # 获取项目信息
        project_name = webhook_data.get('project', {}).get('name', 'unknown')
        author = webhook_data.get('user_name', 'unknown')
        branch = webhook_data.get('ref', '').replace('refs/heads/', '')

        review_result = None
        score = 0
        additions = 0
        deletions = 0
        changes = []        
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_changes(changes)
            
            # 检查版本是否已经审查过
            if version_tracking_enabled and changes:
                existing_review = VersionTracker.is_version_reviewed(project_name, commits, changes)
                if existing_review:
                    logger.info(f'Push version already reviewed for project {project_name}, '
                               f'skipping review. Previous score: {existing_review.get("score", "N/A")}')
                    
                    # 可选：将之前的审查结果重新发布
                    reuse_previous_review = get_env_bool('REUSE_PREVIOUS_REVIEW_RESULT')
                    if reuse_previous_review and existing_review.get('review_result'):
                        previous_result = existing_review['review_result']
                        reuse_note = (f"🔄 **检测到相同版本代码，复用之前的审查结果**\n\n"
                                    f"审查时间: {datetime.fromtimestamp(existing_review['reviewed_at']).strftime('%Y-%m-%d %H:%M:%S')}\n"
                                    f"评分: {existing_review.get('score', 'N/A')}分\n\n"
                                    f"{previous_result}")
                        handler.add_push_notes(reuse_note)
                    
                    # 仍然需要发送事件，但使用之前的审查结果
                    review_result = existing_review.get('review_result', '复用之前的审查结果')
                    score = existing_review.get('score', 0)
                else:
                    # 进行新的审查
                    if not changes:
                        logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
                        review_result = "关注的文件没有修改"
                    else:
                        commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                        review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                        score = CodeReviewer.parse_review_score(review_text=review_result)
                        for item in changes:
                            additions += item['additions']
                            deletions += item['deletions']
                        
                        # 记录版本审查信息
                        VersionTracker.record_version_review(
                            project_name=project_name,
                            commits=commits,
                            changes=changes,
                            author=author,
                            branch=branch,
                            review_type="gitlab_push",
                            review_result=review_result,
                            score=score
                        )
                        logger.info(f'Push version review recorded for project {project_name}')
                    
                    # 将review结果提交到Gitlab的 notes
                    handler.add_push_notes(f'Auto Review Result: \n{review_result}')
            else:
                # 版本追踪未启用或无变更，按原逻辑处理
                if not changes:
                    logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
                    review_result = "关注的文件没有修改"
                else:
                    commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                    review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                    score = CodeReviewer.parse_review_score(review_text=review_result)
                    for item in changes:
                        additions += item['additions']
                        deletions += item['deletions']
                
                # 将review结果提交到Gitlab的 notes
                handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=webhook_data['project']['name'],
            author=webhook_data['user_username'],
            branch=webhook_data['project']['default_branch'],
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=gitlab_url_slug,
            webhook_data=webhook_data,
            additions=additions,
            deletions=deletions,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    '''
    处理Merge Request Hook事件
    :param webhook_data:
    :param gitlab_token:
    :param gitlab_url:
    :param gitlab_url_slug:
    :return:
    '''
    from biz.utils.version_tracker import VersionTracker    
    merge_review_only_protected_branches = get_env_bool('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED')
    # 检查是否启用版本追踪功能
    version_tracking_enabled = get_env_bool('VERSION_TRACKING_ENABLED')
    try:
        # 解析Webhook数据
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Merge Request Hook event received')
        # 如果开启了仅review projected branches的，判断当前目标分支是否为projected branches
        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Merge Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['open', 'update']:
            logger.info(f"Merge Request Hook event, action={handler.action}, ignored.")
            return

        # 仅仅在MR创建或更新时进行Code Review
        # 获取Merge Request的changes
        changes = handler.get_merge_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return
        # 统计本次新增、删除的代码总数
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)        # 获取Merge Request的commits
        commits = handler.get_merge_request_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 获取项目名称
        project_name = webhook_data.get('project', {}).get('name', 'unknown')
        author = webhook_data.get('user', {}).get('name', 'unknown')
        source_branch = webhook_data.get('object_attributes', {}).get('source_branch', '')
        
        # 检查版本是否已经审查过
        if version_tracking_enabled:
            existing_review = VersionTracker.is_version_reviewed(project_name, commits, changes)
            if existing_review:
                logger.info(f'Version already reviewed for project {project_name}, '                           f'skipping review. Previous score: {existing_review.get("score", "N/A")}')
                
                # 可选：将之前的审查结果重新发布到当前MR
                reuse_previous_review = get_env_bool('REUSE_PREVIOUS_REVIEW_RESULT')
                if reuse_previous_review and existing_review.get('review_result'):
                    previous_result = existing_review['review_result']
                    reuse_note = (f"🔄 **检测到相同版本代码，复用之前的审查结果**\n\n"
                                f"审查时间: {datetime.fromtimestamp(existing_review['reviewed_at']).strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"评分: {existing_review.get('score', 'N/A')}分\n\n"
                                f"{previous_result}")
                    handler.add_merge_request_notes(reuse_note)
                
                return
        # review 代码
        commits_text = ';'.join(commit['title'] for commit in commits)
        review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
        
        # 解析审查评分
        review_score = CodeReviewer.parse_review_score(review_text=review_result)

        # 将review结果提交到Gitlab的 notes
        handler.add_merge_request_notes(f'Auto Review Result: \n{review_result}')
        
        # 记录版本审查信息（如果启用了版本追踪）
        if version_tracking_enabled:
            VersionTracker.record_version_review(
                project_name=project_name,
                commits=commits,
                changes=changes,
                author=author,
                branch=source_branch,
                review_type="gitlab_mr",
                review_result=review_result,
                score=review_score
            )
            logger.info(f'Version review recorded for project {project_name}')

        # dispatch merge_request_reviewed event
        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=webhook_data['project']['name'],
                author=webhook_data['user']['username'],
                source_branch=webhook_data['object_attributes']['source_branch'],
                target_branch=webhook_data['object_attributes']['target_branch'],
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=review_score,
                url=webhook_data['object_attributes']['url'],
                review_result=review_result,
                url_slug=gitlab_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
            )
        )

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)

def handle_github_push_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str):
    push_review_enabled = get_env_bool('PUSH_REVIEW_ENABLED')
    try:
        handler = GithubPushHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        additions = 0
        deletions = 0
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_github_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            # 将review结果提交到GitHub的 notes
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=webhook_data['repository']['name'],
            author=webhook_data['sender']['login'],
            branch=webhook_data['ref'].replace('refs/heads/', ''),
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=github_url_slug,
            webhook_data=webhook_data,
            additions=additions,
            deletions=deletions,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_github_pull_request_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str):
    '''
    处理GitHub Pull Request 事件
    :param webhook_data:
    :param github_token:
    :param github_url:
    :param github_url_slug:    :return:
    '''
    merge_review_only_protected_branches = get_env_bool('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED')
    try:
        # 解析Webhook数据
        handler = GithubPullRequestHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Pull Request event received')
        # 如果开启了仅review projected branches的，判断当前目标分支是否为projected branches
        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Merge Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['opened', 'synchronize']:
            logger.info(f"Pull Request Hook event, action={handler.action}, ignored.")
            return

        # 仅仅在PR创建或更新时进行Code Review
        # 获取Pull Request的changes
        changes = handler.get_pull_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_github_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return
        # 统计本次新增、删除的代码总数
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)

        # 获取Pull Request的commits
        commits = handler.get_pull_request_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # review 代码
        commits_text = ';'.join(commit['title'] for commit in commits)
        review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)

        # 将review结果提交到GitHub的 notes
        handler.add_pull_request_notes(f'Auto Review Result: \n{review_result}')

        # dispatch pull_request_reviewed event
        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=webhook_data['repository']['name'],
                author=webhook_data['pull_request']['user']['login'],
                source_branch=webhook_data['pull_request']['head']['ref'],
                target_branch=webhook_data['pull_request']['base']['ref'],
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=webhook_data['pull_request']['html_url'],
                review_result=review_result,
                url_slug=github_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
            ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)
