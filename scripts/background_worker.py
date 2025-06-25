#!/usr/bin/env python3
"""
后台任务处理器 - 可以独立运行或作为服务运行
支持队列模式（RQ）和独立进程模式
"""

import os
import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biz.utils.log import logger
from biz.utils.default_config import get_env_with_default, get_env_bool

def run_rq_worker():
    """运行 RQ 队列工作器"""
    try:
        from redis import Redis
        from rq import Worker, Queue
        
        # 获取 Redis 配置
        redis_url = get_env_with_default('REDIS_URL')
        if redis_url:
            redis_conn = Redis.from_url(redis_url)
        else:
            redis_host = get_env_with_default('REDIS_HOST')
            redis_port = int(get_env_with_default('REDIS_PORT'))
            redis_conn = Redis(host=redis_host, port=redis_port)
        
        # 创建队列列表
        queue_names = ['default', 'gitlab', 'github', 'svn']
        queues = [Queue(name, connection=redis_conn) for name in queue_names]
        
        logger.info(f"🚀 启动 RQ Worker，监听队列: {queue_names}")
        
        # 创建并启动工作器
        worker = Worker(queues, connection=redis_conn)
        worker.work()
        
    except ImportError:
        logger.error("❌ RQ 或 Redis 库未安装，无法启动队列工作器")
        return False
    except Exception as e:
        logger.error(f"❌ RQ Worker 启动失败: {e}")
        return False

def run_svn_worker():
    """运行 SVN 后台检查任务"""
    try:
        from biz.svn.svn_worker import main as svn_main
        
        logger.info("🚀 启动 SVN 后台任务处理器")
        
        # 在单独的线程中运行 SVN 任务
        def svn_worker_thread():
            while True:
                try:
                    svn_main()
                except Exception as e:
                    logger.error(f"❌ SVN 任务执行失败: {e}")
                
                # 等待一段时间后再次执行
                interval = int(get_env_with_default('SVN_CHECK_INTERVAL'))
                time.sleep(interval)
        
        thread = threading.Thread(target=svn_worker_thread, daemon=True)
        thread.start()
        return thread
        
    except ImportError:
        logger.error("❌ SVN 模块未找到")
        return None
    except Exception as e:
        logger.error(f"❌ SVN 任务启动失败: {e}")
        return None

def run_background_tasks():
    """运行所有后台任务"""
    logger.info("🚀 启动后台任务处理器")
    
    # 获取配置
    queue_driver = get_env_with_default('QUEUE_DRIVER')
    svn_enabled = get_env_bool('SVN_CHECK_ENABLED')
    
    tasks = []
    
    # 启动 SVN 后台任务（如果启用）
    if svn_enabled:
        svn_thread = run_svn_worker()
        if svn_thread:
            tasks.append(svn_thread)
    
    # 根据队列驱动类型启动相应的工作器
    if queue_driver == 'rq':
        # RQ 模式 - 运行队列工作器
        logger.info("📦 使用 RQ 队列模式")
        try:
            run_rq_worker()  # 这是阻塞调用
        except KeyboardInterrupt:
            logger.info("⏹️ 收到停止信号，正在关闭后台任务...")
    else:
        # 进程模式 - 只运行非队列任务
        logger.info("🔄 使用进程模式")
        try:
            # 保持主线程运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⏹️ 收到停止信号，正在关闭后台任务...")
    
    logger.info("✅ 后台任务处理器已停止")

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("🚀 AI-CodeReview 后台任务处理器")
    logger.info("=" * 50)
    
    # 检查是否启用后台任务
    enable_worker = get_env_bool('ENABLE_WORKER')
    if not enable_worker:
        logger.info("ℹ️ 后台任务处理器已禁用，退出")
        return 0
    
    try:
        run_background_tasks()
        return 0
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断，正在退出...")
        return 0
    except Exception as e:
        logger.error(f"❌ 后台任务处理器运行失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
