#!/usr/bin/env python3
"""
Docker 日志输出测试脚本
"""
import sys
import time
import logging
from biz.utils.log import logger

def test_logging():
    """测试各种日志级别的输出"""
    print("🧪 开始日志输出测试...")
    print(f"Python 缓冲模式: PYTHONUNBUFFERED={sys.stdout.isatty()}")
    print(f"标准输出编码: {sys.stdout.encoding}")
    
    # 测试 print 输出
    for i in range(3):
        print(f"📝 Print 测试消息 {i+1}")
        sys.stdout.flush()  # 强制刷新
        time.sleep(0.5)
    
    # 测试 logging 输出
    logger.debug("🔍 Debug 级别日志")
    logger.info("ℹ️ Info 级别日志")
    logger.warning("⚠️ Warning 级别日志")
    logger.error("❌ Error 级别日志")
    
    # 测试连续输出
    for i in range(5):
        logger.info(f"🔄 连续日志测试 {i+1}/5")
        time.sleep(0.2)
    
    print("✅ 日志输出测试完成")

if __name__ == "__main__":
    test_logging()
