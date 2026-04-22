from dotenv import load_dotenv

load_dotenv("conf/.env")

import atexit
import json
import os
import signal
import traceback
import threading
import time
from datetime import datetime
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request, jsonify, Response

from biz.gitlab.webhook_handler import slugify_url
from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, \
    handle_github_push_event
from biz.svn.svn_worker import handle_svn_changes, handle_multiple_svn_repositories
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.reporter import Reporter

from biz.utils.config_checker import check_config
from biz.utils.default_config import get_env_bool, get_env_with_default, get_env_int

api_app = Flask(__name__)

# 配置 Flask 应用以支持中文输出
api_app.config['JSON_AS_ASCII'] = False  # 确保 JSON 响应支持中文
api_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True  # 美化 JSON 输出

# 全局配置变量
push_review_enabled = get_env_bool('PUSH_REVIEW_ENABLED')
svn_check_enabled = get_env_bool('SVN_CHECK_ENABLED')

# 后台任务相关全局变量
background_threads = []
scheduler = None


def reload_config():
    """重新加载配置并重新配置定时任务"""
    global push_review_enabled, svn_check_enabled, scheduler
    
    try:
        logger.info("🔄 开始重新加载配置...")
        
        # 重新加载环境变量
        load_dotenv("conf/.env", override=True)
        
        # 更新全局配置变量
        push_review_enabled = get_env_bool('PUSH_REVIEW_ENABLED')
        svn_check_enabled = get_env_bool('SVN_CHECK_ENABLED')
        
        # 🔄 重新配置定时任务（如果调度器已启动）
        if scheduler and scheduler.running:
            logger.info("🔄 检测到调度器正在运行，正在重新配置定时任务...")
            
            # 移除所有现有任务
            old_jobs = scheduler.get_jobs()
            scheduler.remove_all_jobs()
            logger.info(f"已移除 {len(old_jobs)} 个旧的定时任务")
            
            # 重新添加定时任务（不重新创建调度器）
            reconfigure_scheduler_jobs()
            
            new_jobs = scheduler.get_jobs()
            logger.info(f"✅ 已重新配置 {len(new_jobs)} 个定时任务")
        else:
            logger.info("ℹ️ 调度器未运行，跳过定时任务重新配置")
        
        logger.info("✅ API服务配置已重新加载")
        print("[API] 配置已重新加载（包括定时任务）")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API服务重新加载配置失败: {e}")
        print(f"[API] 重新加载配置失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def setup_signal_handlers():
    """设置信号处理器"""
    def signal_handler(signum, frame):
        if hasattr(signal, 'SIGUSR1') and signum == signal.SIGUSR1:
            print("[API] 收到配置重载信号 (SIGUSR1)")
            reload_config()
        elif signum == signal.SIGTERM:
            print("[API] 收到终止信号 (SIGTERM)")
            # 这里可以添加优雅关闭逻辑
            shutdown_background_tasks()
        elif hasattr(signal, 'SIGHUP') and signum == signal.SIGHUP:
            print("[API] 收到重启信号 (SIGHUP)")
            reload_config()
    
    # 注册信号处理器（仅在支持的系统上）
    if hasattr(signal, 'SIGUSR1'):
        signal.signal(signal.SIGUSR1, signal_handler)  # 配置重载
    signal.signal(signal.SIGTERM, signal_handler)  # 优雅关闭
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)   # 重启/重载


# 设置信号处理器
setup_signal_handlers()

@api_app.route('/')
def home():
    svn_status = "已启用" if svn_check_enabled else "未启用"
    
    # 获取SVN仓库信息
    svn_info = ""
    if svn_check_enabled:
        import json
        svn_repositories_config = get_env_with_default('SVN_REPOSITORIES')
        try:
            repositories = json.loads(svn_repositories_config)
            if repositories:
                svn_info = f"<p><strong>配置的SVN仓库:</strong></p><ul>"
                for repo in repositories:
                    name = repo.get('name', 'unknown')
                    url = repo.get('remote_url', 'unknown')
                    svn_info += f"<li>{name}: {url}</li>"
                svn_info += "</ul>"
            else:
                # 检查单仓库配置
                svn_remote_url = get_env_with_default('SVN_REMOTE_URL')
                if svn_remote_url:
                    svn_info = f"<p><strong>SVN仓库:</strong> {svn_remote_url}</p>"
        except json.JSONDecodeError:
            svn_info = "<p><strong>SVN配置:</strong> 配置解析错误</p>"
    
    return f"""<h2>AI代码审查服务正在运行</h2>
              <p><strong>SVN定时检查功能：</strong> {svn_status}</p>
              {svn_info}              <p><strong>GitHub项目地址:</strong> <a href="https://github.com/zhao-zg/AI-CODEREVIEW" target="_blank">
              https://github.com/zhao-zg/AI-CODEREVIEW</a></p>
              <p><strong>Docker镜像:</strong> <a href="https://github.com/zhao-zg/AI-CODEREVIEW/pkgs/container/ai-codereview" target="_blank">
              ghcr.io/zhao-zg/ai-codereview</a></p>
              <p><strong>支持的功能:</strong></p>
              <ul>
                <li>GitLab Webhook 触发审查</li>
                <li>GitHub Webhook 触发审查</li>
                <li>SVN 定时检查审查（支持多仓库）</li>
                <li>手动触发 SVN 检查: <a href="/svn/check" target="_blank">POST /svn/check</a></li>
                <li>手动触发指定仓库: <a href="/svn/check?repo=仓库名" target="_blank">POST /svn/check?repo=仓库名</a></li>
              </ul>
              """


@api_app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "message": "AI Code Review service is running",
        "timestamp": datetime.now().isoformat()
    })


@api_app.route('/review/daily_report', methods=['GET'])
def daily_report():
    # 获取当前日期0点和23点59分59秒的时间戳
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp()

    try:
        if push_review_enabled:
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        if df.empty:
            logger.info("No data to process.")
            return jsonify({'message': 'No data to process.'}), 200
        # 去重：基于 (author, message) 组合
        df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
        # 按照 author 排序
        df_sorted = df_unique.sort_values(by="author")
        # 转换为适合生成日报的格式
        commits = df_sorted.to_dict(orient="records")
        # 生成日报内容
        report_txt = Reporter().generate_report(json.dumps(commits))
        # 发送钉钉通知
        notifier.send_notification(content=report_txt, msg_type="markdown", title="代码提交日报")

        # 返回生成的日报内容
        return json.dumps(report_txt, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'message': f"Failed to generate daily report: {e}"}), 500


def reconfigure_scheduler_jobs():
    """
    重新配置调度器的任务（不重新创建调度器）
    用于配置热重载时重新添加定时任务
    """
    global scheduler, svn_check_enabled
    
    if not scheduler:
        logger.error("调度器未初始化")
        return
    
    try:
        # 1. 添加日报定时任务
        crontab_expression = get_env_with_default('REPORT_CRONTAB_EXPRESSION')
        logger.info(f"📅 配置日报定时任务，cron表达式: '{crontab_expression}'")
        cron_parts = crontab_expression.split()
        
        if len(cron_parts) == 6:
            # 6段式：秒 分 时 日 月 周
            cron_second, cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts
            scheduler.add_job(
                daily_report,
                trigger=CronTrigger(
                    second=cron_second,
                    minute=cron_minute,
                    hour=cron_hour,
                    day=cron_day,
                    month=cron_month,
                    day_of_week=cron_day_of_week
                ),
                id="daily_report",
                name="每日工作日报"
            )
            logger.info(f"✅ 日报定时任务已配置（含秒）: {crontab_expression}")
        elif len(cron_parts) == 5:
            # 5段式：分 时 日 月 周
            cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts
            scheduler.add_job(
                daily_report,
                trigger=CronTrigger(
                    minute=cron_minute,
                    hour=cron_hour,
                    day=cron_day,
                    month=cron_month,
                    day_of_week=cron_day_of_week
                ),
                id="daily_report",
                name="每日工作日报"
            )
            logger.info(f"✅ 日报定时任务已配置: {crontab_expression}")
        else:
            logger.error(f"❌ 日报cron表达式格式错误: '{crontab_expression}'，使用默认值")
            scheduler.add_job(
                daily_report,
                trigger=CronTrigger(minute=0, hour=18, day='*', month='*', day_of_week='mon-fri'),
                id="daily_report",
                name="每日工作日报"
            )
        
        # 2. 添加SVN定时检查任务（如果启用）
        if svn_check_enabled:
            logger.info("📅 配置SVN定时检查任务...")
            
            # 尝试为每个仓库创建独立任务
            svn_repositories_str = get_env_with_default('SVN_REPOSITORIES')
            individual_tasks_created = False
            
            if svn_repositories_str:
                try:
                    import json
                    repositories = json.loads(svn_repositories_str)
                    if isinstance(repositories, list):
                        for repo_config in repositories:
                            repo_name = repo_config.get('name', 'unknown')
                            repo_crontab = repo_config.get('check_crontab')
                            
                            if repo_crontab:
                                svn_cron_parts = repo_crontab.split()
                                
                                if len(svn_cron_parts) == 6:
                                    svn_second, svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                                    scheduler.add_job(
                                        lambda repo=repo_config: trigger_single_svn_repo_check(repo),
                                        trigger=CronTrigger(
                                            second=svn_second,
                                            minute=svn_minute,
                                            hour=svn_hour,
                                            day=svn_day,
                                            month=svn_month,
                                            day_of_week=svn_day_of_week
                                        ),
                                        id=f"svn_check_{repo_name}",
                                        name=f"SVN检查 - {repo_name}"
                                    )
                                    logger.info(f"✅ 仓库 {repo_name} 定时任务已配置（含秒）: {repo_crontab}")
                                    individual_tasks_created = True
                                elif len(svn_cron_parts) == 5:
                                    svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                                    scheduler.add_job(
                                        lambda repo=repo_config: trigger_single_svn_repo_check(repo),
                                        trigger=CronTrigger(
                                            minute=svn_minute,
                                            hour=svn_hour,
                                            day=svn_day,
                                            month=svn_month,
                                            day_of_week=svn_day_of_week
                                        ),
                                        id=f"svn_check_{repo_name}",
                                        name=f"SVN检查 - {repo_name}"
                                    )
                                    logger.info(f"✅ 仓库 {repo_name} 定时任务已配置: {repo_crontab}")
                                    individual_tasks_created = True
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"解析 SVN_REPOSITORIES 配置失败: {e}")
            
            # 创建全局任务（如果需要）
            # 注意：当所有仓库都有独立任务时不创建全局任务，避免同一 revision 被重复处理
            try:
                _repos_for_global = json.loads(svn_repositories_str) if svn_repositories_str else []
                has_repos_without_crontab = any(not r.get('check_crontab') for r in _repos_for_global if isinstance(r, dict))
            except Exception:
                has_repos_without_crontab = True
            if not individual_tasks_created or has_repos_without_crontab:
                svn_crontab = get_env_with_default('SVN_CHECK_CRONTAB')
                svn_cron_parts = svn_crontab.split()
                
                if len(svn_cron_parts) == 6:
                    svn_second, svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                    scheduler.add_job(
                        trigger_svn_check,
                        trigger=CronTrigger(
                            second=svn_second,
                            minute=svn_minute,
                            hour=svn_hour,
                            day=svn_day,
                            month=svn_month,
                            day_of_week=svn_day_of_week
                        ),
                        id="svn_check_global",
                        name="SVN全局检查"
                    )
                    logger.info(f"✅ SVN全局定时任务已配置（含秒）: {svn_crontab}")
                elif len(svn_cron_parts) == 5:
                    svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                    scheduler.add_job(
                        trigger_svn_check,
                        trigger=CronTrigger(
                            minute=svn_minute,
                            hour=svn_hour,
                            day=svn_day,
                            month=svn_month,
                            day_of_week=svn_day_of_week
                        ),
                        id="svn_check_global",
                        name="SVN全局检查"
                    )
                    logger.info(f"✅ SVN全局定时任务已配置: {svn_crontab}")
        else:
            logger.info("ℹ️ SVN检查已禁用，跳过SVN定时任务配置")
        
        logger.info("✅ 所有定时任务重新配置完成")
        
    except Exception as e:
        logger.error(f"❌ 重新配置定时任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def setup_scheduler():
    """
    配置并启动定时任务调度器
    """
    global scheduler
    
    try:
        scheduler = BackgroundScheduler()
          # 日报定时任务
        crontab_expression = get_env_with_default('REPORT_CRONTAB_EXPRESSION')
        logger.info(f"📅 Reading cron expression: '{crontab_expression}'")
        cron_parts = crontab_expression.split()
        logger.info(f"📋 Cron parts after split: {cron_parts} (count: {len(cron_parts)})")
        
        # 验证cron表达式格式（支持5段式和6段式）
        if len(cron_parts) == 6:
            # 6段式：秒 分 时 日 月 周
            cron_second, cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts
            logger.info(f"✅ Cron schedule set (with seconds): second={cron_second}, minute={cron_minute}, hour={cron_hour}, day={cron_day}, month={cron_month}, day_of_week={cron_day_of_week}")
            scheduler.add_job(
                daily_report,
                trigger=CronTrigger(
                    second=cron_second,
                    minute=cron_minute,
                    hour=cron_hour,
                    day=cron_day,
                    month=cron_month,
                    day_of_week=cron_day_of_week
                )
            )
        elif len(cron_parts) == 5:
            # 5段式：分 时 日 月 周（向后兼容）
            cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts
            logger.info(f"✅ Cron schedule set: minute={cron_minute}, hour={cron_hour}, day={cron_day}, month={cron_month}, day_of_week={cron_day_of_week}")
            scheduler.add_job(
                daily_report,
                trigger=CronTrigger(
                    minute=cron_minute,
                    hour=cron_hour,
                    day=cron_day,
                    month=cron_month,
                    day_of_week=cron_day_of_week
                )
            )
        else:
            logger.error(f"❌ Invalid cron expression format: '{crontab_expression}'. Expected 5 or 6 parts, got {len(cron_parts)}")
            logger.info(f"💡 Using default cron expression: '0 18 * * 1-5'")
            cron_parts = '0 18 * * 1-5'.split()
            cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts
            scheduler.add_job(
                daily_report,
                trigger=CronTrigger(
                    minute=cron_minute,
                    hour=cron_hour,
                    day=cron_day,
                    month=cron_month,
                    day_of_week=cron_day_of_week
                )
            )
        
        # SVN定时检查任务
        if svn_check_enabled:
            # 首先尝试从 SVN_REPOSITORIES 配置中为每个仓库创建独立任务
            svn_repositories_str = get_env_with_default('SVN_REPOSITORIES')
            individual_tasks_created = False
            
            if svn_repositories_str:
                try:
                    import json
                    repositories = json.loads(svn_repositories_str)
                    if isinstance(repositories, list):
                        for repo_config in repositories:
                            repo_name = repo_config.get('name', 'unknown')
                            repo_crontab = repo_config.get('check_crontab')
                            
                            if repo_crontab:
                                svn_cron_parts = repo_crontab.split()
                                
                                if len(svn_cron_parts) == 6:
                                    # 6段式：秒 分 时 日 月 周
                                    svn_second, svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                                    scheduler.add_job(
                                        lambda repo=repo_config: trigger_single_svn_repo_check(repo),
                                        trigger=CronTrigger(
                                            second=svn_second,
                                            minute=svn_minute,
                                            hour=svn_hour,
                                            day=svn_day,
                                            month=svn_month,
                                            day_of_week=svn_day_of_week
                                        ),
                                        id=f"svn_check_{repo_name}",
                                        name=f"SVN检查任务 - {repo_name}"
                                    )
                                    logger.info(f"为仓库 {repo_name} 创建独立定时任务（含秒），表达式: {repo_crontab}")
                                    individual_tasks_created = True
                                elif len(svn_cron_parts) == 5:
                                    # 5段式：分 时 日 月 周（向后兼容）
                                    svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                                    scheduler.add_job(
                                        lambda repo=repo_config: trigger_single_svn_repo_check(repo),
                                        trigger=CronTrigger(
                                            minute=svn_minute,
                                            hour=svn_hour,
                                            day=svn_day,
                                            month=svn_month,
                                            day_of_week=svn_day_of_week
                                        ),
                                        id=f"svn_check_{repo_name}",
                                        name=f"SVN检查任务 - {repo_name}"
                                    )
                                    logger.info(f"为仓库 {repo_name} 创建独立定时任务，表达式: {repo_crontab}")
                                    individual_tasks_created = True
                                else:
                                    logger.error(f"仓库 {repo_name} 的定时表达式格式错误: {repo_crontab}，应为5段或6段")
                            else:
                                logger.info(f"仓库 {repo_name} 未配置 check_crontab，将使用全局定时任务")
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"解析 SVN_REPOSITORIES 配置失败: {e}")
            
            # 如果没有为任何仓库创建独立任务，或者有仓库没有配置 check_crontab，则创建全局任务
            # 注意：当所有仓库都有独立任务时不创建全局任务，避免同一 revision 被重复处理
            try:
                _repos_for_global = json.loads(svn_repositories_str) if svn_repositories_str else []
                has_repos_without_crontab = any(not r.get('check_crontab') for r in _repos_for_global if isinstance(r, dict))
            except Exception:
                has_repos_without_crontab = True
            if not individual_tasks_created or has_repos_without_crontab:
                svn_crontab = get_env_with_default('SVN_CHECK_CRONTAB')  # 默认每30分钟检查一次
                svn_cron_parts = svn_crontab.split()
                
                if len(svn_cron_parts) == 6:
                    # 6段式：秒 分 时 日 月 周
                    svn_second, svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                    scheduler.add_job(
                        trigger_svn_check,
                        trigger=CronTrigger(
                            second=svn_second,
                            minute=svn_minute,
                            hour=svn_hour,
                            day=svn_day,
                            month=svn_month,
                            day_of_week=svn_day_of_week
                        ),
                        id="svn_check_global",
                        name="SVN全局检查任务"
                    )
                    logger.info(f"SVN全局定时检查任务已配置（含秒），定时表达式: {svn_crontab}")
                elif len(svn_cron_parts) == 5:
                    # 5段式：分 时 日 月 周（向后兼容）
                    svn_minute, svn_hour, svn_day, svn_month, svn_day_of_week = svn_cron_parts
                    scheduler.add_job(
                        trigger_svn_check,
                        trigger=CronTrigger(
                            minute=svn_minute,
                            hour=svn_hour,
                            day=svn_day,
                            month=svn_month,
                            day_of_week=svn_day_of_week
                        ),
                        id="svn_check_global",
                        name="SVN全局检查任务"
                    )
                    logger.info(f"SVN全局定时检查任务已配置，定时表达式: {svn_crontab}")
                else:
                    logger.error(f"SVN定时表达式格式错误: {svn_crontab}，应为5段或6段")

        # 在启动调度器之前初始化所有SVN仓库
        logger.info("🔄 正在初始化SVN仓库...")
        svn_init_success = initialize_all_svn_repositories()
        
        if svn_init_success:
            logger.info("✅ SVN仓库初始化完成，启动调度器...")
        else:
            logger.warning("⚠️ SVN仓库初始化失败，但仍将启动调度器（定时任务会处理初始化）")

        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully.")        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
        
    except Exception as e:
        logger.error(f"❌ Error setting up scheduler: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")


# 处理 GitLab Merge Request Webhook
@api_app.route('/review/webhook', methods=['POST'])
def handle_webhook():
    # 获取请求的JSON数据
    if request.is_json:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        # 判断是GitLab还是GitHub的webhook
        webhook_source = request.headers.get('X-GitHub-Event')

        if webhook_source:  # GitHub webhook
            return handle_github_webhook(webhook_source, data)
        else:  # GitLab webhook
            return handle_gitlab_webhook(data)
    else:
        return jsonify({'message': 'Invalid data format'}), 400


def handle_github_webhook(event_type, data):    # 获取GitHub配置
    github_token = get_env_with_default('GITHUB_ACCESS_TOKEN') or request.headers.get('X-GitHub-Token')
    if not github_token:
        return jsonify({'message': 'Missing GitHub access token'}), 400

    github_url = get_env_with_default('GITHUB_URL') or 'https://github.com'
    github_url_slug = slugify_url(github_url)

    # 打印整个payload数据
    logger.info(f'Received GitHub event: {event_type}')
    logger.info(f'Payload: {json.dumps(data)}')

    if event_type == "pull_request":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_pull_request_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'GitHub request received(event_type={event_type}), will process asynchronously.'}), 200
    elif event_type == "push":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_push_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'GitHub request received(event_type={event_type}), will process asynchronously.'}), 200
    else:
        error_message = f'Only pull_request and push events are supported for GitHub webhook, but received: {event_type}.'
        logger.error(error_message)
        return jsonify(error_message), 400


def handle_gitlab_webhook(data):
    object_kind = data.get("object_kind")    # 优先从请求头获取，如果没有，则从环境变量获取，如果没有，则从推送事件中获取
    gitlab_url = get_env_with_default('GITLAB_URL') or request.headers.get('X-Gitlab-Instance')
    if not gitlab_url:
        repository = data.get('repository')
        if not repository:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        homepage = repository.get("homepage")
        if not homepage:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        try:
            parsed_url = urlparse(homepage)
            gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        except Exception as e:
            return jsonify({"error": f"Failed to parse homepage URL: {str(e)}"}), 400    # 优先从环境变量获取，如果没有，则从请求头获取
    gitlab_token = get_env_with_default('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
    # 如果gitlab_token为空，返回错误
    if not gitlab_token:
        return jsonify({'message': 'Missing GitLab access token'}), 400

    gitlab_url_slug = slugify_url(gitlab_url)

    # 打印整个payload数据，或根据需求进行处理
    logger.info(f'Received event: {object_kind}')
    logger.info(f'Payload: {json.dumps(data)}')

    # 处理Merge Request Hook
    if object_kind == "merge_request":
        # 创建一个新进程进行异步处理
        handle_queue(handle_merge_request_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
    elif object_kind == "push":
        # 创建一个新进程进行异步处理
        # TODO check if PUSH_REVIEW_ENABLED is needed here
        handle_queue(handle_push_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
    else:
        error_message = f'Only merge_request and push events are supported (both Webhook and System Hook), but received: {object_kind}.'
        logger.error(error_message)
        return jsonify(error_message), 400


@api_app.route('/svn/check', methods=['GET', 'POST'])
def manual_svn_check():
    """手动触发SVN检查"""
    if not svn_check_enabled:
        return jsonify({'message': 'SVN检查功能未启用'}), 400
    
    try:
        # 允许通过查询参数覆盖检查的小时数
        hours_str = request.args.get('hours')
        if hours_str:
            try:
                hours = int(hours_str)
            except ValueError:
                return jsonify({'message': '参数 "hours" 必须是整数'}), 400
        else:
            hours = None

        # 允许通过查询参数指定仓库名称
        repo_name = request.args.get('repo')
        
        # 异步处理SVN检查
        if repo_name:
            # 检查特定仓库
            handle_queue(trigger_specific_svn_repo, repo_name=repo_name, hours=hours)
            message = f'仓库 "{repo_name}" 的SVN检查已启动'
        else:
            # 检查所有仓库
            handle_queue(trigger_svn_check, hours=hours)
            message = 'SVN检查已启动'
        
        # 准备响应消息
        if hours is not None:
            message += f'，将异步处理最近 {hours} 小时的提交。'
        else:
            # 使用默认的24小时
            message += f'，将异步处理最近 24 小时的提交。'

        # 使用自定义响应确保中文正确输出
        response_data = {'message': message}
        import json
        json_str = json.dumps(response_data, ensure_ascii=False, indent=2)
        return Response(json_str, content_type='application/json; charset=utf-8'), 200
    except Exception as e:
        logger.error(f"手动触发SVN检查失败: {e}")
        error_message = f'手动触发SVN检查失败: {str(e)}'
        response_data = {'message': error_message}
        import json
        json_str = json.dumps(response_data, ensure_ascii=False, indent=2)
        return Response(json_str, content_type='application/json; charset=utf-8'), 500


# 添加响应后处理，确保中文编码正确
@api_app.after_request  
def after_request(response):
    """设置响应头以确保中文正确显示"""
    if response.content_type.startswith('application/json'):
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response


def acquire_svn_repo_lock(repo_name: str = "global"):
    """为特定仓库获取互斥锁，成功返回文件对象，失败返回None（跨平台实现）"""
    import os
    import portalocker
    
    # 为每个仓库创建独立的锁文件
    safe_repo_name = "".join(c for c in repo_name if c.isalnum() or c in ('-', '_')).lower()
    lockfile_path = f"log/svn_check_{safe_repo_name}.lock"
    
    try:
        os.makedirs(os.path.dirname(lockfile_path), exist_ok=True)
        lockfile = open(lockfile_path, "w")
        try:
            portalocker.lock(lockfile, portalocker.LOCK_EX | portalocker.LOCK_NB)
            return lockfile
        except portalocker.exceptions.LockException:
            lockfile.close()
            return None
    except Exception:
        return None

def release_svn_repo_lock(lockfile):
    """释放SVN仓库互斥锁（跨平台实现）"""
    import portalocker
    try:
        portalocker.unlock(lockfile)
        lockfile.close()
    except Exception:
        pass

def trigger_specific_svn_repo(repo_name: str, hours: int = None):
    """触发特定SVN仓库的检查（带仓库级互斥锁）"""
    lock = acquire_svn_repo_lock(repo_name)
    if not lock:
        logger.warning(f"仓库 {repo_name} 已有检查任务正在执行，跳过本次触发。")
        return
    try:
        if not svn_check_enabled:
            logger.info("SVN检查功能未启用")
            return
        import json
        check_limit = get_env_int('SVN_CHECK_LIMIT')
        svn_repositories_config = get_env_with_default('SVN_REPOSITORIES')
        try:
            repositories = json.loads(svn_repositories_config)
        except json.JSONDecodeError as e:
            logger.error(f"SVN仓库配置JSON解析失败: {e}")
            return
        target_repo = None
        for repo_config in repositories:
            if repo_config.get('name') == repo_name:
                target_repo = repo_config
                break
        if not target_repo:
            logger.error(f"未找到名为 '{repo_name}' 的仓库配置")
            return
        remote_url = target_repo.get('remote_url')
        local_path = target_repo.get('local_path')
        username = target_repo.get('username')
        password = target_repo.get('password')
        repo_check_hours = hours or target_repo.get('check_hours', 24)
        if not remote_url or not local_path:
            logger.error(f"仓库 {repo_name} 配置不完整")
            return
        logger.info(f"开始检查指定仓库: {repo_name}")
        handle_svn_changes(remote_url, local_path, username, password, repo_check_hours, check_limit, repo_name, "manual", target_repo)
    finally:
        release_svn_repo_lock(lock)


def trigger_svn_check(hours: int = None):
    """触发SVN检查（全局模式使用全局锁）"""
    lock = acquire_svn_repo_lock("global")
    if not lock:
        logger.warning("已有全局SVN检查任务正在执行，跳过本次触发。")
        return
    try:
        if not svn_check_enabled:
            logger.info("SVN检查功能未启用")
            return
        check_limit = get_env_int('SVN_CHECK_LIMIT')    
        svn_repositories_config = get_env_with_default('SVN_REPOSITORIES')
        if svn_repositories_config and svn_repositories_config.strip() != '[]':
            logger.info("使用多仓库配置进行SVN检查")
            logger.debug(f"SVN_REPOSITORIES 配置长度: {len(svn_repositories_config)}")
            logger.debug(f"前50字符: {repr(svn_repositories_config[:50])}")
            logger.debug(f"后10字符: {repr(svn_repositories_config[-10:])}")
            if "'" in svn_repositories_config and '"' not in svn_repositories_config:
                logger.warning("⚠️ 检测到配置中使用了单引号，JSON要求使用双引号")
            handle_multiple_svn_repositories(svn_repositories_config, hours, check_limit, "scheduled")
            return
        svn_remote_url = get_env_with_default('SVN_REMOTE_URL')
        svn_local_path = get_env_with_default('SVN_LOCAL_PATH')
        if not svn_remote_url or not svn_local_path:
            logger.error("SVN_REPOSITORIES 或 SVN_REMOTE_URL+SVN_LOCAL_PATH 环境变量必须设置")
            return
        svn_username = get_env_with_default('SVN_USERNAME')
        svn_password = get_env_with_default('SVN_PASSWORD')
        if hours is None:
            check_hours = get_env_int('SVN_CHECK_INTERVAL_HOURS')
        else:
            check_hours = hours
        logger.info(f"使用单仓库配置进行SVN检查，远程URL: {svn_remote_url}, 本地路径: {svn_local_path}, 检查最近 {check_hours} 小时")
        handle_svn_changes(svn_remote_url, svn_local_path, svn_username, svn_password, check_hours, check_limit, None, "scheduled", None)
    finally:
        release_svn_repo_lock(lock)


def trigger_single_svn_repo_check(repo_config: dict):
    """触发单个SVN仓库检查（带仓库级互斥锁）"""
    repo_name = repo_config.get('name', 'unknown')
    lock = acquire_svn_repo_lock(repo_name)
    if not lock:
        logger.warning(f"仓库 {repo_name} 已有检查任务正在执行，跳过本次检查。")
        return
    try:
        if not svn_check_enabled:
            logger.info("SVN检查功能未启用")
            return
        
        repo_name = repo_config.get('name', 'unknown')
        remote_url = repo_config.get('remote_url')
        local_path = repo_config.get('local_path')
        username = repo_config.get('username')
        password = repo_config.get('password')
        check_hours = repo_config.get('check_hours', 24)
        check_limit = repo_config.get('check_limit', get_env_int('SVN_CHECK_LIMIT'))
        
        if not remote_url or not local_path:
            logger.error(f"仓库 {repo_name} 配置不完整，跳过检查")
            return
        
        logger.info(f"开始独立检查仓库: {repo_name}")
        handle_svn_changes(remote_url, local_path, username, password, check_hours, check_limit, repo_name, "scheduled", repo_config)
        
    except Exception as e:
        error_message = f'单独触发仓库 {repo_config.get("name", "unknown")} 检查时出现错误: {str(e)}\n{traceback.format_exc()}'
        logger.error(error_message)
        from biz.utils.reporter import notifier
        notifier.send_notification(content=error_message)
    finally:
        release_svn_repo_lock(lock)


# 添加配置重载的API端点
@api_app.route('/reload-config', methods=['POST'])
def reload_config_endpoint():
    """配置重载API端点"""
    try:
        reload_config()
        return jsonify({
            "success": True,
            "message": "配置已成功重新加载",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"配置重载失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


def start_background_tasks():
    """启动后台任务（单服务架构）"""
    global background_threads
    
    logger.info("🚀 初始化后台任务...")
    
    # 启动 SVN 后台任务（如果启用）
    svn_enabled = get_env_bool('SVN_CHECK_ENABLED')
    if svn_enabled:
        try:
            from biz.svn.svn_worker import main as svn_main
            
            def svn_worker_thread():
                """SVN工作线程"""
                try:
                    logger.info("🚀 启动 SVN 后台任务处理器")
                    # 只执行一次，由调度器控制频率
                    svn_main()
                except Exception as e:
                    logger.error(f"❌ SVN 任务执行失败: {e}")
            
            # 在单独线程中启动SVN任务
            thread = threading.Thread(target=svn_worker_thread, daemon=True)
            thread.start()
            background_threads.append(thread)
            logger.info("✅ SVN 后台任务已启动")
            
        except ImportError as e:
            logger.error(f"❌ SVN 后台任务启动失败 (缺少依赖): {e}")
        except Exception as e:
            logger.error(f"❌ SVN 后台任务启动失败: {e}")
    else:
        logger.info("ℹ️ SVN 检查已禁用")
    
    logger.info("✅ 后台任务初始化完成")

def shutdown_background_tasks():
    """关闭后台任务"""
    global background_threads, scheduler
    
    logger.info("⏹️ 正在关闭后台任务...")
    
    # 关闭调度器
    if scheduler:
        scheduler.shutdown()
    
    # 等待后台线程结束
    for thread in background_threads:
        if thread.is_alive():
            logger.info(f"等待线程 {thread.name} 结束...")
            thread.join(timeout=5)
    
    logger.info("✅ 后台任务已关闭")
    
@api_app.route('/review/retry', methods=['POST'])
def retry_review():
    """
    管理员触发的重新AI评审接口
    传入参数：type（mr/push/svn/github）、唯一标识（如id/commit_sha/version_hash）
    """
    data = request.get_json()
    review_type = data.get('type')
    identifier = data.get('id') or data.get('commit_sha') or data.get('version_hash')
    if not review_type or not identifier:
        return jsonify({"success": False, "message": "缺少type或唯一标识参数"}), 400
    try:
        from biz.service.review_service import ReviewService
        result = ReviewService.retry_review(review_type, identifier)
        return jsonify(result)
    except Exception as e:
        logger.error(f"重新评审失败: {e}")
        return jsonify({"success": False, "message": f"重新评审失败: {e}"}), 500


def initialize_all_svn_repositories():
    """在启动定时器前初始化所有SVN仓库"""
    try:
        if not svn_check_enabled:
            logger.info("SVN检查功能未启用，跳过SVN仓库初始化")
            return True
        
        logger.info("开始初始化SVN仓库...")
        
        # 获取SVN仓库配置
        svn_repositories_config = get_env_with_default('SVN_REPOSITORIES')
        
        if svn_repositories_config and svn_repositories_config.strip() != '[]':
            # 多仓库模式
            import json
            try:
                repositories = json.loads(svn_repositories_config)
                if isinstance(repositories, list):
                    logger.info(f"发现 {len(repositories)} 个SVN仓库配置，开始初始化...")
                    
                    for repo_config in repositories:
                        repo_name = repo_config.get('name', 'unknown')
                        remote_url = repo_config.get('remote_url')
                        local_path = repo_config.get('local_path')
                        username = repo_config.get('username')
                        password = repo_config.get('password')
                        
                        if not remote_url or not local_path:
                            logger.warning(f"仓库 {repo_name} 配置不完整，跳过初始化")
                            continue
                        
                        try:
                            logger.info(f"初始化仓库: {repo_name}")
                            from biz.svn.svn_handler import SVNHandler
                            
                            # 创建SVN处理器并初始化工作副本
                            svn_handler = SVNHandler(remote_url, local_path, username, password)
                            svn_handler._prepare_working_copy()
                            
                            logger.info(f"✅ 仓库 {repo_name} 初始化完成")
                            
                        except Exception as e:
                            logger.error(f"❌ 仓库 {repo_name} 初始化失败: {str(e)}")
                            # 继续初始化其他仓库，不因单个仓库失败而停止
                            continue
                    
                    logger.info("✅ 多仓库SVN初始化完成")
                    return True
                    
                else:
                    logger.error("SVN_REPOSITORIES 配置格式错误，必须是数组")
                    return False
                    
            except json.JSONDecodeError as e:
                logger.error(f"解析 SVN_REPOSITORIES 配置失败: {e}")
                return False
        else:
            # 单仓库模式（向后兼容）
            svn_remote_url = get_env_with_default('SVN_REMOTE_URL')
            svn_local_path = get_env_with_default('SVN_LOCAL_PATH')
            svn_username = get_env_with_default('SVN_USERNAME')
            svn_password = get_env_with_default('SVN_PASSWORD')
            
            if svn_remote_url and svn_local_path:
                try:
                    logger.info("初始化单SVN仓库...")
                    from biz.svn.svn_handler import SVNHandler
                    
                    svn_handler = SVNHandler(svn_remote_url, svn_local_path, svn_username, svn_password)
                    svn_handler._prepare_working_copy()
                    
                    logger.info("✅ 单SVN仓库初始化完成")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ 单SVN仓库初始化失败: {str(e)}")
                    return False
            else:
                logger.info("未配置SVN仓库，跳过初始化")
                return True
                
    except Exception as e:
        logger.error(f"❌ SVN仓库初始化过程出现异常: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False


if __name__ == '__main__':
    try:
        logger.info("🚀 启动 AI-CodeReview 统一服务")
        
        check_config()
        
        # 启动定时任务调度器
        setup_scheduler()
        
        # 启动后台任务
        start_background_tasks()
        
        # 初始化SVN仓库
        initialize_all_svn_repositories()
        
        # 启动Flask API服务
        port = get_env_int('API_PORT')
        logger.info("=" * 60)
        logger.info("🚀 AI-CodeReview API 服务启动中...")
        logger.info(f"🌐 服务地址: http://0.0.0.0:{port}")
        logger.info(f"📊 日志级别: {logger.level}")
        logger.info(f"🔧 配置检查: {'✅ 通过' if check_config() else '❌ 失败'}")
        logger.info(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # 注册优雅关闭处理
        atexit.register(shutdown_background_tasks)
        
        # 启动 Flask 应用，在 Docker 环境下使用调试模式便于查看日志
        debug_mode = os.getenv('DOCKER_ENV') == 'true'
        api_app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("⏹️ 收到停止信号，正在关闭服务...")
        shutdown_background_tasks()
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}")
        shutdown_background_tasks()
        raise


