import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient, extract_assistant_message
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.default_config import get_env_with_default, get_env_int


class QwenClient(BaseClient):
    supports_tools = True

    # 阿里云百炼约定（2026-08）：qwen3 全系（qwen3 / qwen3.5 / qwen3.7 / qwen3.8-max...）
    # 支持 enable_thinking + thinking_budget；旧模型（qwen-coder-plus / qwen-max / qwen2.5）不支持，
    # 传了会被忽略，故仅对 qwen3 系下发思考参数。
    _THINKING_MODEL_RE = re.compile(r"^qwen3", re.IGNORECASE)

    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("QWEN_API_KEY")
        self.base_url = get_env_with_default("QWEN_API_BASE_URL")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = get_env_with_default("QWEN_API_MODEL")
        self.thinking_level = (get_env_with_default("QWEN_THINKING_LEVEL") or "high").lower().strip()
        self.context_window = get_env_int("QWEN_CONTEXT_WINDOW", 131072)

    def _build_extra_body(self, model: str) -> Dict[str, Any]:
        """简化规则：开启思考 → 只传 enable_thinking + thinking_budget（不传 temperature）；
        off → 关闭思考并传低温 temperature 保证审查输出稳定。

        仅 qwen3 系支持 enable_thinking；旧模型（qwen-coder-plus 等）只传 temperature。
        """
        level = self.thinking_level
        if not self._THINKING_MODEL_RE.match(model or ""):
            return {"temperature": 0.2}
        if level == "off":
            return {"enable_thinking": False, "temperature": 0.2}
        budget = {"low": 2048, "medium": 4096, "high": 8192, "max": 16384}.get(level, 4096)
        return {"enable_thinking": True, "thinking_budget": budget}

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body=self._build_extra_body(model),
        )
        return completion.choices[0].message.content

    def completions_with_tools(self,
                                messages: List[Dict[str, Any]],
                                tools: List[Dict[str, Any]],
                                model: Optional[str] | NotGiven = NOT_GIVEN,
                                ) -> Dict[str, Any]:
        model = model or self.default_model
        kwargs = {"model": model, "messages": messages, "extra_body": self._build_extra_body(model)}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        completion = self.client.chat.completions.create(**kwargs)
        message = completion.choices[0].message
        assistant_message, tool_calls = extract_assistant_message(message)
        return {"content": message.content, "tool_calls": tool_calls, "assistant_message": assistant_message}
