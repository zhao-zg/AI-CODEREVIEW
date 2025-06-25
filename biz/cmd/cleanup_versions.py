#!/usr/bin/env python3
"""
版本追踪定时清理任务
Scheduled cleanup task for version tracking
"""

import os
import sys
import time
import schedule
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biz.utils.version_tracker import VersionTracker
from biz.utils.default_config import get_env_int, get_env_bool
from biz.utils.log import logger


def cleanup_old_versions():
    """清理旧版本记录"""
    try:        # 从环境变量获取配置
        retention_days = get_env_int('VERSION_TRACKING_RETENTION_DAYS')
        
        logger.info(f"开始清理 {retention_days} 天前的版本记录...")
        
        # 执行清理
        deleted_count = VersionTracker.cleanup_old_records(retention_days)
        
        if deleted_count > 0:
            logger.info(f"成功清理了 {deleted_count} 条旧版本记录")
        else:
            logger.info("没有需要清理的版本记录")
            
    except Exception as e:
        logger.error(f"版本记录清理失败: {e}")


def run_scheduler():
    """运行定时任务调度器"""    # 检查是否启用版本追踪
    if not get_env_bool('VERSION_TRACKING_ENABLED'):
        logger.info("版本追踪功能未启用，跳过定时清理任务")
        return
    
    # 设置定时任务
    # 每天凌晨2点执行清理
    schedule.every().day.at("02:00").do(cleanup_old_versions)
    
    # 也可以设置为每周执行一次
    # schedule.every().sunday.at("02:00").do(cleanup_old_versions)
    
    logger.info("版本追踪定时清理任务已启动，将在每天凌晨2点执行清理")
    logger.info("按 Ctrl+C 停止定时任务")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("定时清理任务已停止")


if __name__ == '__main__':
    # 可以通过命令行参数决定是运行一次性清理还是启动定时任务
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 执行一次性清理
        cleanup_old_versions()
    else:
        # 启动定时任务
        run_scheduler()
