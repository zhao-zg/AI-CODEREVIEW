import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient, extract_assistant_message
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger
from biz.utils.default_config import get_env_with_default, get_env_int


class DeepSeekClient(BaseClient):
    supports_tools = True

    # DeepSeek 官方约定（2026-08 更新，api-docs.deepseek.com/guides/thinking_mode）：
    # - 当前模型为 deepseek-v4-pro / deepseek-v4-flash（旧 deepseek-chat/deepseek-reasoner 逐步下线）；
    # - 思考模式开关：extra_body={"thinking": {"type": "enabled/disabled"}}，默认开启、默认 effort=high；
    # - effort 控制：顶层参数 reasoning_effort，取值 low / high / xhigh / max；
    # - 思考模式下 temperature/top_p/presence_penalty/frequency_penalty 全部无效（传了也不报错）；
    # - 思考模式 + 工具调用时，reasoning_content 必须随历史回传，否则 400（agentic 审查链路注意）。
    # 官方温度建议：Coding/Math → 0.0。审查场景关闭思考时用 0.0。
    _EFFORT_MAP = {"low": "low", "medium": "high", "high": "high", "max": "max"}

    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("DEEPSEEK_API_KEY")
        self.base_url = get_env_with_default("DEEPSEEK_API_BASE_URL")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) # DeepSeek supports OpenAI API SDK
        self.default_model = get_env_with_default("DEEPSEEK_API_MODEL")
        self.thinking_level = (get_env_with_default("DEEPSEEK_THINKING_LEVEL") or "high").lower().strip()
        self.context_window = get_env_int("DEEPSEEK_CONTEXT_WINDOW", 65536)

    def _build_extra_kwargs(self, model: str) -> Dict[str, Any]:
        """根据思考程度构造请求参数（按 DeepSeek 官方 2026 约定）。

        - off：关闭思考，此时 temperature 生效（思考模式下无效），代码审查用官方建议的 0.0；
        - low/medium/high/max：开启思考，映射 reasoning_effort（low/high/high/max；
          DeepSeek 无 medium 档，medium 对齐官方默认 high），思考模式下不传 temperature；
        - deepseek-reasoner（旧 R1）始终深度思考、不接受任何控制参数，返回空保持官方默认。
        """
        level = self.thinking_level
        if "reasoner" in (model or "").lower():
            return {}
        if level == "off":
            return {"extra_body": {"thinking": {"type": "disabled"}}, "temperature": 0.0}
        return {
            "reasoning_effort": self._EFFORT_MAP.get(level, "high"),
            "extra_body": {"thinking": {"type": "enabled"}},
        }

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        try:
            model = model or self.default_model
            logger.debug(f"Sending request to DeepSeek API. Model: {model}, Messages: {messages}")
            
            kwargs = {"model": model, "messages": messages}
            kwargs.update(self._build_extra_kwargs(model))
            completion = self.client.chat.completions.create(**kwargs)
            
            if not completion or not completion.choices:
                logger.error("Empty response from DeepSeek API")
                return "AI服务返回为空，请稍后重试"
                
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            # 检查是否是认证错误
            if "401" in str(e):
                return "DeepSeek API认证失败，请检查API密钥是否正确"
            elif "404" in str(e):
                return "DeepSeek API接口未找到，请检查API地址是否正确"
            else:
                return f"调用DeepSeek API时出错: {str(e)}"

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
