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
from biz.utils.config_manager import ConfigManager

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
            process_svn_commit(svn_handler, commit, svn_local_path, display_name, trigger_type, repo_config)
            
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
    """
    try:
        revision = commit['revision']
        author = commit['author']
        message = commit['message']
        logger.info(f'处理SVN提交: r{revision} by {author}')

        # === Merge提交检查 ===
        if repo_config and should_skip_merge_commit(repo_config, message):
            logger.info(f'跳过merge提交 r{revision}: {message[:100]}...')
            return
        # === Merge提交检查 END ===

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
        version_tracking_enabled = get_config_bool('VERSION_TRACKING_ENABLED')
        if version_tracking_enabled:
            # 检查该revision是否已审查
            existing_review = VersionTracker.is_version_reviewed(project_name, commit_info, changes)
            if existing_review:
                logger.info(f'SVN版本 r{revision} 已审查，跳过重复审查。')
                return
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
                diff_struct_json = json.dumps(diff_struct, ensure_ascii=False, indent=2)
                commits_text = f"SVN提交 r{revision}: {message}"
                review_result = CodeReviewer().review_and_strip_code(diff_struct_json, commits_text)
                if review_result and review_result.strip() and review_result != "代码为空":
                    
                    score = CodeReviewer.parse_review_score(review_text=review_result)
                    review_successful = True
                    logger.info(f'代码审查完成，评分: {score}')
                else:
                    logger.warning(f'代码审查失败：审查结果为空或无效，不写入数据库')
                    return
            except Exception as e:
                logger.error(f'代码审查过程中发生异常: {e}，不写入数据库')
                return
        elif svn_review_enabled:
            logger.info(f'SVN提交 r{revision} 没有包含需要审查的文件，跳过审查')
            review_result = "无需要审查的文件"
            review_successful = True
        else:
            logger.info(f'SVN代码审查未启用，跳过审查')
            review_result = "SVN代码审查未启用"
            review_successful = True

        if not review_successful:
            logger.warning(f'SVN提交 r{revision} 审查未成功，不进行事件触发和通知')
            return

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
        if version_tracking_enabled:
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


def is_merge_commit(message: str) -> bool:
    """
    判断提交信息是否为merge提交
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
    
    # 常见的merge提交模式
    merge_patterns = [
        'merged ',
        'merge branch',
        'merge pull request',
        'merge pr ',
        'auto-merged',
        'auto merge',
        'merging ',
        'merge from ',
        'merge to ',
        'merge into ',
        'merge of ',
        'merge:',
        'merge - ',
        # SVN特有的merge模式
        'merged via svn merge',
        'merge r',
        'merge rev'
    ]
    
    # 检查是否匹配任何merge模式
    for pattern in merge_patterns:
        if pattern in message_lower:
            return True
    
    # 如果消息完全就是"merge"
    if message_lower == 'merge':
        return True
    
    return False


def should_skip_merge_commit(repo_config: dict, commit_message: str) -> bool:
    """
    根据仓库配置判断是否应该跳过merge提交
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
