import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient, extract_assistant_message
from biz.llm.types import NotGiven, NOT_GIVEN


from biz.utils.default_config import get_env_with_default, get_env_int


class OpenAIClient(BaseClient):
    supports_tools = True

    # 通用 OpenAI 兼容网关（OAI）：官方 OpenAI 及第三方 OAI 兼容模型均走此通道。
    # 典型场景：走 new-api/one-api 等转换型中转站接入 DeepSeek/Qwen/Kimi 等模型。
    #
    # 简化规则：
    # - 开启思考（low/medium/high/max）：只传 reasoning_effort，不传 temperature；
    #   转换型中转站会负责把 reasoning_effort 翻译成下游各家的原生思考参数
    #   （DeepSeek→thinking/effort、Qwen→enable_thinking 等）；
    # - 关闭思考（off）：传低温 temperature 0.2 保证审查输出稳定。
    # 注意：gpt-4o 等旧的非推理模型不支持 reasoning_effort，使用它们时请保持思考档位为 off。

    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("OPENAI_API_KEY")
        self.base_url = get_env_with_default("OPENAI_API_BASE_URL")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = get_env_with_default("OPENAI_API_MODEL")
        self.thinking_level = (get_env_with_default("OPENAI_THINKING_LEVEL") or "high").lower().strip()
        self.context_window = get_env_int("OPENAI_CONTEXT_WINDOW", 131072)

    def _build_extra_kwargs(self, model: str) -> Dict[str, Any]:
        """开启思考 → 只传 reasoning_effort（不传 temperature）；off → 低温 temperature 0.2。

        思考档位 → reasoning_effort 的通用映射由转换型中转站（如 new-api）翻译为下游原生参数。
        """
        level = self.thinking_level
        if level == "off":
            return {"temperature": 0.2}
        effort_map = {"low": "low", "medium": "medium", "high": "high", "max": "high"}
        return {"reasoning_effort": effort_map.get(level, "medium")}

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
