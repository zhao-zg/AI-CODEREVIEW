import os

from biz.llm.client.base import BaseClient
from biz.llm.client.deepseek import DeepSeekClient
from biz.llm.client.ollama_client import OllamaClient
from biz.llm.client.openai import OpenAIClient
from biz.llm.client.qwen import QwenClient
from biz.llm.client.zhipuai import ZhipuAIClient
from biz.utils.log import logger

from biz.utils.default_config import get_env_with_default


class Factory:
    @staticmethod
    def getClient(provider: str = None) -> BaseClient:
        provider = provider or get_env_with_default("LLM_PROVIDER")
        chat_model_providers = {
            'zhipuai': lambda: ZhipuAIClient(),
            'openai': lambda: OpenAIClient(),
            'deepseek': lambda: DeepSeekClient(),
            'qwen': lambda: QwenClient(),
            'ollama': lambda : OllamaClient()
        }

        provider_func = chat_model_providers.get(provider)
        if provider_func:
            return provider_func()
        else:
            raise Exception(f'Unknown chat model provider: {provider}')
