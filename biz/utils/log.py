import logging
import os
from logging.handlers import TimedRotatingFileHandler
from biz.utils.default_config import get_env_with_default, get_env_int

# 自定义 Logger 类，重写 warn 和 error 方法
class CustomLogger(logging.Logger):
    def warn(self, msg, *args, **kwargs):
        # 在 warn 消息前添加 ⚠️
        msg_with_emoji = f"⚠️ {msg}"
        super().warning(msg_with_emoji, *args, **kwargs)  # 注意：warn 是 warning 的别名

    def error(self, msg, *args, **kwargs):
        # 在 error 消息前添加 ❌
        msg_with_emoji = f"❌ {msg}"
        super().error(msg_with_emoji, *args, **kwargs)


log_file = get_env_with_default("LOG_FILE", "log/app.log")
# 日志保留天数，默认30天（1个月）
log_retention_days = get_env_int("LOG_RETENTION_DAYS", 30)
# 设置日志级别
log_level = get_env_with_default("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level.upper(), logging.INFO)

# 确保日志目录存在
log_dir = os.path.dirname(log_file)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# 使用TimedRotatingFileHandler按天轮换日志
file_handler = TimedRotatingFileHandler(
    filename=log_file,
    when='midnight',        # 每天午夜轮换
    interval=1,             # 间隔1天
    backupCount=log_retention_days,  # 保留指定天数的日志
    encoding='utf-8',
    delay=False
)
# 设置日志文件名后缀为日期格式
file_handler.suffix = "%Y-%m-%d"
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'))
file_handler.setLevel(LOG_LEVEL)

console_handler = logging.StreamHandler()
# Docker 环境下的控制台日志格式更简洁，便于查看
if os.getenv('DOCKER_ENV') == 'true':
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'))
else:
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'))
console_handler.setLevel(LOG_LEVEL)

# 强制刷新控制台输出（Docker 环境特别重要）
console_handler.stream.flush = lambda: None
if hasattr(console_handler.stream, 'flush'):
    console_handler.stream.flush()


# 使用自定义的 Logger 类
logger = CustomLogger(__name__)
logger.setLevel(LOG_LEVEL)  # 设置 Logger 的日志级别
logger.addHandler(file_handler)
logger.addHandler(console_handler)
