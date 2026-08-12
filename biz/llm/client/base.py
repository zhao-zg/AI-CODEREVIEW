import json
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


def extract_assistant_message(message) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    将 OpenAI 兼容 SDK 返回的 assistant message 对象转换为：
    1. 可以直接 append 回对话历史的 assistant 消息 dict；
    2. 结构化的工具调用列表 [{"id","name","arguments"}]（arguments 已解析为 dict）。

    兼容 openai/deepseek/qwen/zhipuai 等使用同一套 function calling 响应结构的 SDK。

    注意（2026-08 DeepSeek 官方约定）：思考模式 + 工具调用时，模型返回的 reasoning_content
    （思考链）必须随 assistant 消息回传，否则后续请求会返回 400。因此这里会把
    reasoning_content 一并序列化进 assistant_message；各家思考字段名不同
    （DeepSeek=reasoning_content，Qwen=reasoning_content，GLM=reasoning），用 getattr 统一兼容。
    """
    assistant_message: Dict[str, Any] = {
        "role": "assistant",
        "content": message.content or "",
    }
    # 思考链字段透传（思考模式 + 工具调用的多轮对话必须回传，否则 DeepSeek 返回 400）
    for field in ("reasoning_content", "reasoning"):
        value = getattr(message, field, None)
        if value:
            assistant_message[field] = value
            break
    tool_calls: List[Dict[str, Any]] = []
    raw_tool_calls = getattr(message, "tool_calls", None)
    if raw_tool_calls:
        serialized_calls = []
        for tc in raw_tool_calls:
            serialized_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            })
            try:
                arguments = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": arguments})
        assistant_message["tool_calls"] = serialized_calls
    return assistant_message, tool_calls


class BaseClient:
    """ Base class for chat models client. """

    # 子类若支持 function calling（工具调用），应设置为 True 并覆盖 completions_with_tools
    supports_tools: bool = False

    def ping(self) -> bool:
        """Ping the model to check connectivity."""
        try:
            result = self.completions(messages=[{"role": "user", "content": '请仅返回 "ok"。'}])
            return result and result == 'ok'
        except Exception:
            logger.error("尝试连接LLM失败， {e}")
            return False

    @abstractmethod
    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        """Chat with the model.
        """

    def completions_with_tools(self,
                                messages: List[Dict[str, Any]],
                                tools: List[Dict[str, Any]],
                                model: Optional[str] | NotGiven = NOT_GIVEN,
                                ) -> Dict[str, Any]:
        """
        支持工具调用（function calling）的对话补全。

        默认实现用于不支持工具调用的客户端：忽略 tools，直接退化为普通 completions，
        tool_calls 恒为空列表，调用方据此可以判断出"本轮无需调用工具，直接使用 content 作为最终结果"。
        支持 function calling 的客户端（如 openai/deepseek/qwen/zhipuai）应覆盖此方法并设置 supports_tools=True。

        Returns:
            dict: {
                "content": str,              # 模型返回的文本内容
                "tool_calls": List[Dict],    # 结构化工具调用 [{"id","name","arguments"}]，无工具调用时为空列表
                "assistant_message": Dict,   # 可直接 append 到对话历史的 assistant 消息
            }
        """
        content = self.completions(messages, model=model)
        return {
            "content": content,
            "tool_calls": [],
            "assistant_message": {"role": "assistant", "content": content},
        }
