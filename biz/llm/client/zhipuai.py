import os
from typing import Any, Dict, List, Optional

from zhipuai import ZhipuAI

from biz.llm.client.base import BaseClient, extract_assistant_message
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.default_config import get_env_with_default, get_env_int


class ZhipuAIClient(BaseClient):
    supports_tools = True

    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = ZhipuAI(api_key=api_key)
        self.default_model = get_env_with_default("ZHIPUAI_API_MODEL")
        self.thinking_level = (get_env_with_default("ZHIPUAI_THINKING_LEVEL") or "high").lower().strip()
        self.context_window = get_env_int("ZHIPUAI_CONTEXT_WINDOW", 1048576)

    def _build_extra_kwargs(self, model: str) -> Dict[str, Any]:
        """简化规则：开启思考 → 只传 thinking（不传 temperature）；off → 低温 temperature。

        GLM-4.5+ / GLM-5.x 为思考模型（不接受 temperature）；glm-4-flash 等旧模型不支持
        thinking，使用它们时请保持思考档位为 off。
        """
        level = self.thinking_level
        if level == "off":
            return {"temperature": 0.2}
        return {"extra_body": {"thinking": {"type": "enabled"}}}

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model
        kwargs = {"model": model, "messages": messages}
        kwargs.update(self._build_extra_kwargs(model))
        completion = self.client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content

    def completions_with_tools(self,
                                messages: List[Dict[str, Any]],
                                tools: List[Dict[str, Any]],
                                model: Optional[str] | NotGiven = NOT_GIVEN,
                                ) -> Dict[str, Any]:
        model = model or self.default_model
        kwargs = {"model": model, "messages": messages}
        kwargs.update(self._build_extra_kwargs(model))
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        completion = self.client.chat.completions.create(**kwargs)
        message = completion.choices[0].message
        assistant_message, tool_calls = extract_assistant_message(message)
        return {"content": message.content, "tool_calls": tool_calls, "assistant_message": assistant_message}
