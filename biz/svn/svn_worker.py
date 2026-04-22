import os
import json
import traceback
from datetime import datetime
from typing import List, Dict

from biz.entity.review_entity import SvnReviewEntity
from biz.event.event_manager import event_manager
from biz.svn.svn_handler import SVNHandler, filter_svn_changes
from biz.utils.code_reviewer import CodeReviewer, is_api_error_message
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.config_manager import ConfigManager

# === SVN增量检查集成 ===
from biz.utils.svn_checkpoint import SVNCheckpointManager
# === SVN增量检查集成 END ===

def get_config_bool(key: str, default: bool = False) -> bool:
    """从 ConfigManager 获取布尔值配置"""
    try:
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        value = env_config.get(key, '0' if not default else '1')
        return value.lower() in ('1', 'true', 'yes', 'on')
    except:
        return default

def get_config_str(key: str, default: str = '') -> str:
    """从 ConfigManager 获取字符串配置"""
    try:
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        return env_config.get(key, default)
    except:
        return default

def get_config_int(key: str, default: int = 0) -> int:
    """从 ConfigManager 获取整数配置"""
    try:
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        value = env_config.get(key, str(default))
        return int(value)
    except:
        return default
# === 版本追踪集成 ===
from biz.utils.version_tracker import VersionTracker
# === 版本追踪集成 END ===


# === 简单的revision缓存（内存级别） ===
_processed_revisions_cache = {}  # 格式: {repo_name: {revision: timestamp}}
_cache_ttl = 3600  # 缓存1小时

def _clean_revision_cache(repo_name: str):
    """清理指定仓库的过期缓存"""
    try:
        current_time = int(datetime.now().timestamp())
        if repo_name not in _processed_revisions_cache:
            return
        repo_cache = _processed_revisions_cache[repo_name]
        expired_revisions = [
            rev for rev, timestamp in repo_cache.items()
            if current_time - timestamp > _cache_ttl
        ]
        for rev in expired_revisions:
            del repo_cache[rev]
    except Exception as e:
        logger.warning(f'清理revision缓存失败: {e}')


def is_revision_recently_processed(repo_name: str, revision: str) -> bool:
    """
    检查revision是否在最近已经处理过（只读，不写入缓存）
    """
    try:
        if repo_name not in _processed_revisions_cache:
            return False
        _clean_revision_cache(repo_name)
        if revision in _processed_revisions_cache.get(repo_name, {}):
            logger.debug(f'Revision r{revision} 在缓存中找到，跳过处理')
            return True
        return False
    except Exception as e:
        logger.warning(f'检查revision缓存失败: {e}')
        return False


def mark_revision_processed(repo_name: str, revision: str):
    """将revision标记为已处理（在成功处理后调用）"""
    try:
        if repo_name not in _processed_revisions_cache:
            _processed_revisions_cache[repo_name] = {}
        _processed_revisions_cache[repo_name][revision] = int(datetime.now().timestamp())
    except Exception as e:
        logger.warning(f'写入revision缓存失败: {e}')

# === 简单的revision缓存 END ===


def handle_multiple_svn_repositories(repositories_config: str = None, check_hours: int = None, check_limit: int = 100, trigger_type: str = "scheduled"):
    """
    处理多个SVN仓库的变更
    :param repositories_config: SVN仓库配置JSON字符串，如果为None则从环境变量读取
    :param check_hours: 检查最近多少小时的变更，如果为None则使用各仓库的配置
    """
    try:
        # 解析仓库配置
        if repositories_config is None:
            repositories_config = get_config_str('SVN_REPOSITORIES')
          # 详细的配置调试信息
        logger.debug(f"SVN仓库配置字符串长度: {len(repositories_config)}")
        logger.debug(f"SVN仓库配置前50字符: {repr(repositories_config[:50])}")
          # 尝试自动修复常见的JSON格式问题
        original_config = repositories_config
        
        # 修复1: 去除可能的BOM字符（优先处理）
        if repositories_config.startswith('\ufeff'):
            logger.warning("⚠️ 检测到BOM字符，自动移除")
            repositories_config = repositories_config[1:]
        
        # 修复2: 清理多余的空白字符
        repositories_config = repositories_config.strip()
          # 修复3: 处理引号问题
        if "'" in repositories_config and '"' not in repositories_config:
            logger.warning("⚠️ 检测到配置使用单引号，自动转换为双引号")
            repositories_config = repositories_config.replace("'", '"')
        elif '"' not in repositories_config and ':' in repositories_config:
            # 修复4: 处理完全没有引号的情况（如 {name:value} 格式）
            logger.warning("⚠️ 检测到配置缺少引号，尝试自动添加引号")
            repositories_config = _fix_unquoted_json(repositories_config)
        
        if repositories_config != original_config:
            logger.info("✅ 已自动修复配置格式问题")
        
        try:
            repositories = json.loads(repositories_config)
        except json.JSONDecodeError as e:
            logger.error(f"SVN仓库配置JSON解析失败: {e}")
            logger.error(f"配置内容: {repr(repositories_config)}")
            logger.error(f"错误位置: 行{e.lineno}, 列{e.colno}, 字符{e.pos}")
            
            # 尝试显示错误上下文
            if e.pos < len(repositories_config):
                error_char = repositories_config[e.pos]
                logger.error(f"错误字符: {repr(error_char)} (ASCII: {ord(error_char)})")
                
                # 显示错误周围的字符
                start = max(0, e.pos - 10)
                end = min(len(repositories_config), e.pos + 10)
                context = repositories_config[start:end]
                logger.error(f"错误上下文: {repr(context)}")
            return
        
        if not repositories:
            logger.info("没有配置SVN仓库")
            return
        
        logger.info(f"开始检查 {len(repositories)} 个SVN仓库")
        
        # 检查仓库配置唯一性，避免 name 重复
        seen_keys = set()
        for repo_config in repositories:
            repo_name = repo_config.get('name', 'unknown')
            if repo_name in seen_keys:
                logger.error(f"检测到重复的仓库配置: name={repo_name}，请确保唯一！")
                notifier.send_notification(content=f"❌ 检测到重复的SVN仓库配置：\nname={repo_name}\n请检查配置，确保每个仓库唯一！")
                return
            seen_keys.add(repo_name)
        
        # 处理每个仓库
        for repo_config in repositories:
            try:
                repo_name = repo_config.get('name', 'unknown')
                remote_url = repo_config.get('remote_url')
                local_path = repo_config.get('local_path')
                username = repo_config.get('username')
                password = repo_config.get('password')
                repo_check_hours = check_hours or repo_config.get('check_hours', 24)
                # 使用仓库特定的check_limit，如果没有则使用全局默认值
                repo_check_limit = repo_config.get('check_limit', check_limit)
                
                if not remote_url or not local_path:
                    logger.error(f"仓库 {repo_name} 配置不完整，跳过")
                    continue
                
                logger.info(f"开始检查仓库: {repo_name}")
                handle_svn_changes(remote_url, local_path, username, password, repo_check_hours, repo_check_limit, repo_name, trigger_type, repo_config)
                
            except Exception as e:
                error_message = f'处理仓库 {repo_config.get("name", "unknown")} 时出现错误: {str(e)}\n{traceback.format_exc()}'
                logger.error(error_message)
                notifier.send_notification(content=error_message)
                
    except Exception as e:
        error_message = f'多仓库SVN变更检测出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('多仓库SVN变更检测出现未知错误: %s', error_message)


def handle_svn_changes(svn_remote_url: str, svn_local_path: str, svn_username: str = None, svn_password: str = None, check_hours: int = 24, check_limit: int = 100, repo_name: str = None, trigger_type: str = "scheduled", repo_config: dict = None):
    """
    处理SVN变更事件 - 支持增量检查
    :param svn_remote_url: SVN远程仓库URL
    :param svn_local_path: SVN本地路径
    :param svn_username: SVN用户名
    :param svn_password: SVN密码
    :param check_hours: 检查最近多少小时的变更（仅在手动触发时使用）
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
        
        # === 增量检查逻辑 ===
        # 定时任务自动使用增量检查，手动触发使用固定时间窗口
        if trigger_type == "scheduled":
            # 定时任务使用增量检查
            # 初始化检查点管理器
            SVNCheckpointManager.init_db()
            
            # 获取上次检查时间
            last_check_time = SVNCheckpointManager.get_last_check_time(display_name)
            current_time = int(datetime.now().timestamp())
            
            # 计算实际的检查时间范围（小时）
            actual_check_hours = (current_time - last_check_time) / 3600
            
            logger.info(f'仓库 {display_name} 使用增量检查，上次检查: {datetime.fromtimestamp(last_check_time)}, 检查范围: {actual_check_hours:.1f} 小时')
            
            # 获取最近的提交（基于上次检查时间）
            recent_commits = svn_handler.get_recent_commits(hours=actual_check_hours, limit=check_limit)
        else:
            # 手动触发使用固定时间窗口
            logger.info(f'仓库 {display_name} 使用固定时间窗口检查，检查范围: {check_hours} 小时')
            recent_commits = svn_handler.get_recent_commits(hours=check_hours, limit=check_limit)
        # === 增量检查逻辑 END ===
        
        if not recent_commits:
            logger.info(f'仓库 {display_name} 没有发现最近的SVN提交')
            
            # 即使没有新提交，也要更新检查点（定时任务）
            if trigger_type == "scheduled":
                SVNCheckpointManager.update_checkpoint(display_name)
            
            return
        
        logger.info(f'仓库 {display_name} 发现 {len(recent_commits)} 个最近的提交')
        
        # 记录处理的最新revision（用于更新检查点）
        latest_revision = None
        processed_count = 0
        
        # 处理每个提交
        for commit in recent_commits:
            revision = commit.get('revision', '')
            
            # === 简单的revision重复检查 ===
            if revision and is_revision_recently_processed(display_name, revision):
                logger.info(f'SVN r{revision} 最近已处理，跳过')
                continue
            # === 简单的revision重复检查 END ===

            # 提前写入缓存，防止并发任务（如独立任务和全局任务同时触发）重复处理同一 revision
            if revision:
                mark_revision_processed(display_name, revision)

            # 处理提交（所有情况都会返回结果，包括错误信息）
            process_svn_commit(svn_handler, commit, svn_local_path, display_name, trigger_type, repo_config)
            processed_count += 1
            
            # 记录最新处理的revision
            if revision and (not latest_revision or int(revision) > int(latest_revision)):
                latest_revision = revision
        
        logger.info(f'仓库 {display_name} 实际处理了 {processed_count} 个提交')
        
        # 更新检查点（定时任务）
        if trigger_type == "scheduled":
            SVNCheckpointManager.update_checkpoint(display_name, latest_revision)
            
    except Exception as e:
        display_name = repo_name or os.path.basename(svn_local_path)
        error_message = f'仓库 {display_name} SVN变更检测出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('SVN变更检测出现未知错误: %s', error_message)


def process_svn_commit(svn_handler: SVNHandler, commit: Dict, svn_path: str, repo_name: str = None, trigger_type: str = "scheduled", repo_config: dict = None):
    """
    处理单个SVN提交，使用结构化diff JSON输入AI审查
    :param svn_handler: SVN处理器
    :param commit: 提交信息
    :param svn_path: SVN路径
    :param repo_name: 仓库名称
    注意：所有情况都会处理并记录结果（包括错误信息作为审查结果）
    """
    try:
        revision = commit['revision']
        author = commit['author']
        message = commit['message']
        logger.info(f'处理SVN提交: r{revision} by {author}')

        # === Merge提交检查 ===
        if repo_config:
            # 使用增强检测（如果启用）或传统检测
            from biz.utils.default_config import get_env_bool
            use_enhanced = get_env_bool('USE_ENHANCED_MERGE_DETECTION', False)
            
            if use_enhanced:
                should_skip = should_skip_merge_commit_enhanced(repo_config, commit, svn_handler)
            else:
                should_skip = should_skip_merge_commit(repo_config, message)
            
            if should_skip:
                logger.info(f'跳过merge提交 r{revision}: {message[:100]}...')
                return  # merge提交跳过，直接返回
        # === Merge提交检查 END ===

        # 获取提交的变更
        changes = svn_handler.get_commit_changes(commit)
        logger.info(f'变更文件数: {len(changes)}')

        # 过滤变更
        changes = filter_svn_changes(changes)

        if not changes:
            logger.info(f'提交 r{revision} 没有包含需要审查的文件类型')
            return  # 没有需要审查的文件，直接返回
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
        version_tracking_enabled = get_config_bool('VERSION_TRACKING_ENABLED')
        if version_tracking_enabled:
            # 检查该revision是否已审查
            existing_review = VersionTracker.is_version_reviewed(project_name, commit_info, changes)
            if existing_review:
                logger.info(f'SVN版本 r{revision} 已审查，跳过重复审查。')
                return  # 已审查的提交，直接返回
        # === 版本追踪集成 END ===

        review_result = ""
        score = 0
        review_successful = False
        svn_review_enabled = get_config_bool('SVN_REVIEW_ENABLED')

        if svn_review_enabled and changes:
            try:
                # 构造结构化diff JSON
                files_json = []
                for change in changes:
                    # 补充status/action字段
                    status = change.get('action', '')
                    files_json.append({
                        'file_path': change.get('full_path') or change.get('new_path'),
                        'status': status,  # A/M/D等
                        'diff_content': change.get('diff', ''),
                        'additions': change.get('additions', 0),
                        'deletions': change.get('deletions', 0)
                    })
                
                diff_struct = {
                    'files': files_json,
                    'commits': commit_info
                }
                # 传递结构化diff给AI
                diff_struct_json = json.dumps(files_json, ensure_ascii=False, indent=2)
                #commits_text = f"SVN提交 r{revision}: {message}"
                commits_text = json.dumps(commit_info, ensure_ascii=False, indent=2)
                review_result = CodeReviewer().review_and_strip_code(diff_struct_json, commits_text)
                # 无论审查结果如何（包括错误信息），都记录并处理
                if review_result and review_result.strip():
                    if is_api_error_message(review_result):
                        logger.warning(f'代码审查遇到API错误，错误信息已作为审查结果: {review_result[:200]}...')
                        score = 0
                    else:
                        score = CodeReviewer.parse_review_score(review_text=review_result)
                        logger.info(f'代码审查完成，评分: {score}')
                    review_successful = True
                else:
                    logger.warning(f'代码审查返回空结果，使用默认消息')
                    review_result = "代码审查返回空结果"
                    score = 0
                    review_successful = True
            except Exception as e:
                logger.error(f'代码审查过程中发生异常: {e}，将异常信息作为审查结果')
                review_result = f"❌ AI审查失败: 代码审查过程异常\n\n详细信息:\n- 错误类型: {type(e).__name__}\n- 错误消息: {str(e)}\n- 建议: 请查看日志获取更多信息"
                score = 0
                review_successful = True
        elif svn_review_enabled:
            logger.info(f'SVN提交 r{revision} 没有包含需要审查的文件，跳过审查')
            review_result = "无需要审查的文件"
            review_successful = True
        else:
            logger.info(f'SVN代码审查未启用，跳过审查')
            review_result = "SVN代码审查未启用"
            review_successful = True

        # 所有情况都认为审查成功（包括错误信息作为审查结果）
        # 因此不再需要检查 review_successful

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
            trigger_type=trigger_type
        ))

        # 注意：通知已经通过事件管理器发送，不需要重复发送
        # 原来的直接通知代码已移除，避免重复推送
        
        # === 版本追踪集成 ===
        version_tracking_enabled = get_config_bool('VERSION_TRACKING_ENABLED', True)
        if version_tracking_enabled and not is_api_error_message(review_result):
            VersionTracker.record_version_review(
                project_name=project_name,
                commits=commit_info,
                changes=changes,
                author=author,
                branch='',
                review_type='svn',
                review_result=review_result,
                score=score,
                commit_message=message,
                commit_date=commit['date'],
                additions_count=additions,
                deletions_count=deletions
            )
            logger.info(f'SVN版本 r{revision} 审查结果已记录到版本追踪（包含详细信息）。')

    except Exception as e:
        error_message = f'处理SVN提交 r{commit.get("revision", "unknown")} 时出现错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('处理SVN提交时出现错误: %s', error_message)
        # 异常情况也不影响检查点更新


def is_merge_commit(message: str) -> bool:
    """
    判断提交信息是否为merge提交（基础版本，保持向后兼容）
    常见的merge提交信息模式：
    - "Merged ..."
    - "Merge branch ..."
    - "Merge pull request ..." 
    - "Auto-merged ..."
    - 包含 "merge" 关键词的其他模式
    """
    if not message:
        return False
    
    message_lower = message.lower().strip()
    
    # 增强的merge提交模式（使用正则表达式）
    import re
    merge_patterns = [
        r'merged?\s+.*from\s+',      # "merged xxx from yyy"
        r'merged?\s+.*into\s+',      # "merged xxx into yyy"
        r'merged?\s+.*to\s+',        # "merged xxx to yyy"
        r'merged?\s+/branches',      # "merged /branches/xxx"
        r'merged?\s+r?\d+',          # "merged r12345"  
        r'merged?\s+branch',         # "merged branch xxx"
        r'merge\s+branch',           # "merge branch"
        r'merge\s+pull\s+request',   # "merge pull request"
        r'merge\s+pr\s+',            # "merge pr #123"
        r'auto-?merged?',            # "auto-merged" or "automerged"
        r'merged?\s+via\s+svn',      # "merged via svn"
        r'^merged?$',                # 单独的"merge"或"merged"
        r'merge\s*[:;-]',            # "merge:" or "merge-"
        r'merging\s+',               # "merging changes"
        r'merge\s+from\s+',          # "merge from trunk"
        r'merge\s+to\s+',            # "merge to branch"
        r'merge\s+into\s+',          # "merge into main"
        r'merge\s+of\s+',            # "merge of changes"
        r'merge\s+rev',              # "merge rev"
        r'合并\s*[:;-]',             # 中文的"合并:"或"合并-"
        r'合并\s*分支',              # "合并分支"
        r'合并\s*请求',              # "合并请求"
        r'合并\s*提交',              # "合并提交"
        r'合并\s*变更',              # "合并变更"
        r'合并\s*代码',              # "合并代码"
        r'合并\s*到',                # "合并到"
        r'合并\s*从',                # "合并从"
        r'合并\s*主线',              # "合并主线"
        r'合并了修改版本号',          # "合并了修改版本号"
    ]
    
    # 检查是否匹配任何merge模式
    for pattern in merge_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


def is_merge_commit_enhanced(commit: Dict, svn_handler=None) -> Dict:
    """
    增强的merge提交检测，支持多维度分析
    
    Args:
        commit: SVN提交信息字典
        svn_handler: SVN处理器实例（可选）
    
    Returns:
        检测结果字典：{
            'is_merge': bool,
            'confidence': float,
            'detection_methods': list,
            'evidence': dict
        }
    """
    result = {
        'is_merge': False,
        'confidence': 0.0,
        'detection_methods': [],
        'evidence': {}
    }
    
    message = commit.get('message', '')
    revision = commit.get('revision', '')
    paths = commit.get('paths', [])
    author = commit.get('author', '')
    
    # 1. 基于提交消息的检测（权重40%）
    if is_merge_commit(message):
        result['detection_methods'].append('message')
        result['evidence']['message'] = {'patterns_matched': True}
        result['confidence'] += 0.4
    
    # 2. 基于文件路径和数量的检测（权重30%）
    path_indicators = []
    
    # 大量文件修改（可能是merge）
    if len(paths) > 20:
        path_indicators.append(f'large_file_count: {len(paths)} files')
        result['confidence'] += 0.15
    elif len(paths) > 10:
        path_indicators.append(f'moderate_file_count: {len(paths)} files')
        result['confidence'] += 0.1
    
    # 检查分支相关路径
    import re
    branch_paths = []
    for path_info in paths:
        path = path_info.get('path', '')
        if re.search(r'/(branches?|trunk|tags?)/|_(branch|dev|feature)_', path, re.IGNORECASE):
            branch_paths.append(path)
    
    if branch_paths:
        path_indicators.append(f'branch_paths: {len(branch_paths)} paths')
        result['confidence'] += 0.15
    
    if path_indicators:
        result['detection_methods'].append('paths')
        result['evidence']['paths'] = path_indicators
    
    # 3. 基于变更统计的检测（权重20%）
    stats_indicators = []
    
    # 统计变更类型
    actions = {}
    for path_info in paths:
        action = path_info.get('action', 'M')
        actions[action] = actions.get(action, 0) + 1
    
    total_changes = len(paths)
    if total_changes > 15:
        stats_indicators.append(f'large_changeset: {total_changes} files')
        result['confidence'] += 0.1
    
    # 修改占比高（merge常见特征）
    if total_changes > 0:
        mod_ratio = actions.get('M', 0) / total_changes
        if mod_ratio > 0.8:
            stats_indicators.append(f'high_modification_ratio: {mod_ratio:.2f}')
            result['confidence'] += 0.1
    
    if stats_indicators:
        result['detection_methods'].append('stats')
        result['evidence']['stats'] = stats_indicators
    
    # 4. 基于作者模式的检测（权重10%）
    time_indicators = []
    automated_authors = ['buildbot', 'jenkins', 'ci', 'auto', 'merge', 'system']
    if any(bot in author.lower() for bot in automated_authors):
        time_indicators.append(f'automated_author: {author}')
        result['confidence'] += 0.1
    
    if time_indicators:
        result['detection_methods'].append('time')
        result['evidence']['time'] = time_indicators
    
    # 最终判断（置信度阈值可配置）
    from biz.utils.default_config import get_env_with_default
    confidence_threshold = float(get_env_with_default('MERGE_DETECTION_THRESHOLD', '0.4'))
    
    # 修复浮点数精度问题，添加小的容差 (1e-10)
    result['is_merge'] = (result['confidence'] + 1e-10) >= confidence_threshold
    result['confidence'] = min(1.0, result['confidence'])
    
    return result


def should_skip_merge_commit(repo_config: dict, commit_message: str) -> bool:
    """
    根据仓库配置判断是否应该跳过merge提交（传统方法）
    :param repo_config: 仓库配置字典
    :param commit_message: 提交消息
    :return: True表示应该跳过，False表示应该处理
    """
    # 检查是否为merge提交
    if not is_merge_commit(commit_message):
        return False  # 不是merge提交，不跳过
    
    # 获取仓库的merge配置，默认为True（审查merge提交）
    enable_merge_review = repo_config.get('enable_merge_review', True)
    
    # 如果禁用了merge审查，则跳过
    if not enable_merge_review:
        logger.info(f'Merge提交已禁用审查，跳过: {commit_message[:100]}...')
        return True
    
    return False  # 启用了merge审查，不跳过


def should_skip_merge_commit_enhanced(repo_config: dict, commit: Dict, svn_handler=None) -> bool:
    """
    增强版本的merge提交跳过判断
    
    Args:
        repo_config: 仓库配置字典
        commit: 完整的提交信息字典
        svn_handler: SVN处理器实例（可选）
    
    Returns:
        True表示应该跳过，False表示应该处理
    """
    from biz.utils.default_config import get_env_bool
    
    # 检查是否启用增强检测
    use_enhanced_detection = get_env_bool('USE_ENHANCED_MERGE_DETECTION', False)
    
    if use_enhanced_detection:
        # 使用增强检测
        detection_result = is_merge_commit_enhanced(commit, svn_handler)
        is_merge = detection_result['is_merge']
        
        if is_merge:
            logger.info(f'增强检测识别为merge提交 (置信度: {detection_result["confidence"]:.2f}, '
                       f'方法: {", ".join(detection_result["detection_methods"])}): '
                       f'{commit.get("message", "")[:100]}...')
    else:
        # 使用传统检测
        is_merge = is_merge_commit(commit.get('message', ''))
    
    if not is_merge:
        return False  # 不是merge提交，不跳过
    
    # 获取仓库的merge配置，默认为True（审查merge提交）
    enable_merge_review = repo_config.get('enable_merge_review', True)
    
    # 如果禁用了merge审查，则跳过
    if not enable_merge_review:
        logger.info(f'Merge提交已禁用审查，跳过: {commit.get("message", "")[:100]}...')
        return True
    
    return False  # 启用了merge审查，不跳过


def _fix_unquoted_json(config_str: str) -> str:
    """
    修复无引号的JSON配置
    将 {name:value,key:value} 格式转换为 {"name":"value","key":"value"} 格式
    """
    import re
    
    try:
        # 这是一个简化的修复，适用于基本的键值对
        # 模式: 匹配键值对格式 key:value
        
        # 1. 为所有的键添加双引号 (如果还没有引号的话)
        # 匹配模式: 逗号或左括号后的单词（键）
        config_str = re.sub(r'([,\[\{]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', config_str)
        
        # 2. 为字符串值添加双引号（排除数字）
        # 匹配模式: 冒号后的非数字值（不包含引号、逗号、括号的字符串）
        config_str = re.sub(r':\s*([^",\}\]\d][^",\}\]]*?)(\s*[,\}\]])', r':"\1"\2', config_str)
        
        # 3. 处理开头的情况（第一个键）
        config_str = re.sub(r'^(\s*\[\s*\{\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', config_str)
        
        logger.debug(f"JSON修复结果: {config_str[:100]}...")
        return config_str
        
    except Exception as e:
        logger.error(f"JSON自动修复失败: {e}")
        return config_str


def main():
    """SVN 后台任务主函数"""
    try:
        logger.info("🚀 启动 SVN 后台检查任务")
        
        # 检查 SVN 是否启用
        if not get_config_bool('SVN_CHECK_ENABLED'):
            logger.info("ℹ️ SVN 检查已禁用")
            return
        
        # 获取配置
        repositories_config = get_config_str('SVN_REPOSITORIES')
        check_limit = get_config_int('SVN_CHECK_LIMIT')
        
        if not repositories_config:
            logger.warning("⚠️ 未配置 SVN 仓库，跳过 SVN 检查")
            return
        
        logger.info(f"📂 开始检查 SVN 仓库: {repositories_config[:50]}...")
        
        # 执行 SVN 检查
        handle_multiple_svn_repositories(
            repositories_config=repositories_config,
            check_limit=check_limit
        )
        
        logger.info("✅ SVN 检查任务完成")
        
    except Exception as e:
        logger.error(f"❌ SVN 后台任务执行失败: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
