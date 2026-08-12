import os
import re
from typing import Dict, List, Optional

from ollama import ChatResponse
from ollama import Client

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.default_config import get_env_with_default, get_env_int


class OllamaClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.default_model = get_env_with_default("OLLAMA_API_MODEL")
        self.base_url = get_env_with_default("OLLAMA_API_BASE_URL")
        self.client = Client(
            host=self.base_url,
        )
        self.thinking_level = (get_env_with_default("OLLAMA_THINKING_LEVEL") or "high").lower().strip()
        self.context_window = get_env_int("OLLAMA_CONTEXT_WINDOW", 65536)

    def _build_chat_kwargs(self, model: str) -> Dict:
        """简化规则：开启思考 → think=True（不传 temperature）；off → think=False + 低温 temperature。"""
        level = self.thinking_level
        if level == "off":
            return {"think": False, "options": {"temperature": 0.2}}
        return {"think": True}

    def _extract_content(self, content: str) -> str:
        """
        从内容中提取<think>...</think>标签之外的部分。

        Args:
            content (str): 原始内容。

        Returns:
            str: 提取后的内容。
        """
        if "<think>" in content and "</think>" not in content:
            # 大模型回复的时候，思考链有可能截断，那么果断忽略回复，返回空
            return "COT ABORT!"
        elif "<think>" not in content and "</think>" in content:
            return content.split("</think>", 1)[1].strip()
        elif re.search(r'<think>.*?</think>', content, re.DOTALL):
            return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model
        kwargs = {"model": model, "messages": messages}
        kwargs.update(self._build_chat_kwargs(model))
        try:
            response: ChatResponse = self.client.chat(**kwargs)
        except TypeError:
            # 旧版 ollama SDK 不支持 think 顶层参数：降级重试（思考程度不生效，其余参数保留）
            kwargs.pop("think", None)
            response: ChatResponse = self.client.chat(**kwargs)
        content = response['message']['content']
        return self._extract_content(content)
