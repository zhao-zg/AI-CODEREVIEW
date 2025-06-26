import os

from dotenv import load_dotenv

from biz.llm.factory import Factory
from biz.utils.log import logger

# 指定环境变量文件路径
ENV_FILE_PATH = "conf/.env"
load_dotenv(ENV_FILE_PATH)


REQUIRED_ENV_VARS = [
    #"LLM_PROVIDER",
]

# 允许的 LLM 供应商
LLM_PROVIDERS = {"zhipuai", "openai", "deepseek", "jedi", "ollama", "qwen"}

# 每种供应商必须配置的键
LLM_REQUIRED_KEYS = {
    "zhipuai": ["ZHIPUAI_API_KEY", "ZHIPUAI_API_MODEL"],
    "openai": ["OPENAI_API_KEY", "OPENAI_API_MODEL"],
    "deepseek": ["DEEPSEEK_API_KEY", "DEEPSEEK_API_MODEL"],
    "jedi": ["JEDI_API_KEY", "JEDI_API_BASE_URL", "JEDI_API_MODEL"],
    "ollama": ["OLLAMA_API_BASE_URL", "OLLAMA_API_MODEL"],
    "qwen": ["QWEN_API_KEY", "QWEN_API_MODEL"],
}


def check_env_vars():
    """检查环境变量"""
    missing_vars = [var for var in REQUIRED_ENV_VARS if var not in os.environ]
    if missing_vars:
        logger.warning(f"缺少环境变量: {', '.join(missing_vars)}")
        return False
    else:
        logger.info("所有必要的环境变量均已设置。")
        return True

def check_config():
    """主检查入口"""
    logger.info("开始检查配置项...")
    env_check_passed = check_env_vars()
    logger.info("配置项检查完成。")
    return env_check_passed