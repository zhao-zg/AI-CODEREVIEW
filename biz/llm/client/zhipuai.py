import os
from typing import Dict, List, Optional

from zhipuai import ZhipuAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.default_config import get_env_with_default


class ZhipuAIClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = ZhipuAI(api_key=api_key)
        self.default_model = get_env_with_default("ZHIPUAI_API_MODEL")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return completion.choices[0].message.content
