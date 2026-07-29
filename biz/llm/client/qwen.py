import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient, extract_assistant_message
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.default_config import get_env_with_default


class QwenClient(BaseClient):
    supports_tools = True

    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("QWEN_API_KEY")
        self.base_url = get_env_with_default("QWEN_API_BASE_URL")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = get_env_with_default("QWEN_API_MODEL")
        self.extra_body={"enable_thinking": False}

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body=self.extra_body,
        )
        return completion.choices[0].message.content

    def completions_with_tools(self,
                                messages: List[Dict[str, Any]],
                                tools: List[Dict[str, Any]],
                                model: Optional[str] | NotGiven = NOT_GIVEN,
                                ) -> Dict[str, Any]:
        model = model or self.default_model
        kwargs = {"model": model, "messages": messages, "extra_body": self.extra_body}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        completion = self.client.chat.completions.create(**kwargs)
        message = completion.choices[0].message
        assistant_message, tool_calls = extract_assistant_message(message)
        return {"content": message.content, "tool_calls": tool_calls, "assistant_message": assistant_message}
