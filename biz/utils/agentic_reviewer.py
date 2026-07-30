"""
支持工具调用（function calling）的代码审查器。

与 BatchCodeReviewer 的区别：审查过程中 AI 可以在给出最终结论前，主动调用工具
（读取工作副本内某个文件的完整内容 / 在代码库中检索关键字）来补充"只看 diff"
天然缺失的上下文（例如函数签名变化的影响范围、diff 上下文行数之外看不到的完整函数体等），
从而降低因上下文不足导致的误判/漏判。

两种工具调用方式：
1. 原生 function calling：客户端 BaseClient.supports_tools=True 时使用（openai/deepseek/qwen/zhipuai），
   通过 completions_with_tools() 走各家 SDK 标准的 tools/tool_calls 协议。
2. 纯文本协议模拟：客户端不支持原生 function calling 时使用（如 ollama、jedi 这类自定义/无 tools
   参数支持的客户端），通过在 prompt 里约定"输出一行 tool_call JSON"的文本约定，解析普通文本
   回复来模拟工具调用。任何只接受 messages 列表的 completions() 实现都能兼容这种方式。

未提供 tool_context 时，自动降级为与 BatchCodeReviewer 完全一致的单轮/分批审查，不影响现有行为。
"""
import json
import re
from typing import Any, Callable, Dict, List, Optional

from biz.utils.code_reviewer import BatchCodeReviewer, is_api_error_message
from biz.utils.default_config import get_env_with_default, get_env_int
from biz.utils.log import logger

# 工具的 JSON Schema 声明（OpenAI function calling 格式），用于原生 function calling 路径。
# 工具名需要与调用方传入的 tool_context 字典的 key 一一对应。
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "读取工作副本中某个文件的完整内容，用于查看diff之外的上下文"
                "（如完整函数体、类定义、import列表等）。仅能读取本次审查所属仓库工作副本内的文件。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "相对于仓库根目录的文件路径，例如 biz/utils/foo.py",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "在整个代码仓库工作副本中检索一个关键字（函数名/类名/变量名等），"
                "用于确认某个改动的影响范围、是否还有其他调用方。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要检索的关键字，例如函数名、类名、变量名"},
                    "max_results": {"type": "integer", "description": "最多返回的匹配行数，默认20，最多50"},
                },
                "required": ["query"],
            },
        },
    },
]

# 纯文本协议路径追加给 system prompt 的说明：不支持原生 function calling 的客户端
# （ollama/jedi 等）靠这段文字约定来"模拟"工具调用，解析回复文本而非结构化 tool_calls。
_TEXT_PROTOCOL_INSTRUCTIONS = """

### 工具调用格式（纯文本协议，当前模型不支持原生 function calling，请严格遵守）
如果需要调用工具获取更多信息，请只输出一行严格的 JSON，不要包含任何其他文字、解释或 markdown 代码块，格式如下：
{"tool_call": {"name": "工具名", "arguments": {"参数名": "参数值"}}}

可用工具与参数：
- read_file：{"file_path": "相对于仓库根目录的文件路径"}
- search_code：{"query": "关键字", "max_results": 20}

我会把工具执行结果发给你，你可以继续调用工具（最多若干轮），或者在获得足够信息后直接输出最终审查报告
（此时不能输出 tool_call JSON，必须是完整的 Markdown 审查报告）。
"""


class AgenticCodeReviewer(BatchCodeReviewer):
    """在 BatchCodeReviewer 的分批/合并框架上，为每一批审查增加工具调用能力。"""

    def __init__(self, tool_context: Optional[Dict[str, Callable]] = None):
        super().__init__()
        # 使用专门的 agentic prompt（在核心原则/评分标准基础上增加工具使用说明），
        # 评分标准与 code_review_batch_prompt 保持一致，确保口径统一。
        self.prompts = self._load_prompts("code_review_agentic_prompt", get_env_with_default("REVIEW_STYLE"))
        self.tool_context = tool_context or {}
        self.max_tool_rounds = get_env_int("AGENTIC_REVIEW_MAX_TOOL_ROUNDS", 5)

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """审查一批代码；若未提供工具上下文，自动降级为普通单轮审查。"""
        if not self.tool_context:
            return super().review_code(diffs_text, commits_text)
        if getattr(self.client, "supports_tools", False):
            return self._review_with_native_tools(diffs_text, commits_text)
        return self._review_with_text_protocol(diffs_text, commits_text)

    def _review_with_native_tools(self, diffs_text: str, commits_text: str) -> str:
        """原生 function calling 路径；最终仍失败（如返回API错误消息）时降级为不带工具调用的
        普通审查，保证本次提交至少能拿到一次正常审查结果，而不是让整次审查彻底失败。"""
        result = self._run_native_tools_loop(diffs_text, commits_text)
        if is_api_error_message(result):
            logger.warning("原生工具调用审查最终失败，降级为不带工具调用的普通审查，确保本次提交仍能拿到审查结果")
            return super().review_code(diffs_text, commits_text)
        return result

    def _run_native_tools_loop(self, diffs_text: str, commits_text: str) -> str:
        """原生 function calling 路径（openai/deepseek/qwen/zhipuai 等 supports_tools=True 的客户端）。"""
        messages: List[Dict[str, Any]] = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]

        for round_idx in range(self.max_tool_rounds):
            response = self.client.completions_with_tools(messages, TOOLS_SCHEMA)
            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                return response.get("content") or ""

            messages.append(response["assistant_message"])
            logger.info(f"AI审查请求调用工具 (原生协议, 第{round_idx + 1}轮): {[c['name'] for c in tool_calls]}")
            for call in tool_calls:
                result_text = self._dispatch_tool(call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result_text,
                })

        # 达到最大轮数仍未结束：强制要求模型直接给出结论，避免无限调用工具
        logger.warning(f"AI审查已达到最大工具调用轮数({self.max_tool_rounds})，强制要求给出最终结论")
        messages.append({
            "role": "user",
            "content": "已达到本次审查的最大工具调用次数，请直接基于当前已获得的信息给出最终审查报告，不要再调用工具。",
        })
        response = self.client.completions_with_tools(messages, [])
        return response.get("content") or ""

    def _review_with_text_protocol(self, diffs_text: str, commits_text: str) -> str:
        """纯文本协议模拟路径；最终仍失败时同样降级为不带工具调用的普通审查。

        实测发现（2026-07-30 生产日志）：像多文件Java diff这类内容容易让模型在推理末尾
        自行决定"该调用工具了"，从而触发它自己内置的原生工具调用倾向（即使我们从未通过
        API传过tools参数），导致网关返回不完整响应；这种情况对同一份diff可能连续多次复现
        （温度较低，推理路径相近），单纯重试未必能解决，所以必须有这道最终兜底。"""
        result = self._run_text_protocol_loop(diffs_text, commits_text)
        if is_api_error_message(result):
            logger.warning("文本协议模拟审查最终失败，降级为不带工具调用的普通审查，确保本次提交仍能拿到审查结果")
            return super().review_code(diffs_text, commits_text)
        return result

    def _run_text_protocol_loop(self, diffs_text: str, commits_text: str) -> str:
        """
        纯文本协议模拟路径（ollama/jedi 等不支持原生 function calling 的客户端）。
        通过普通的 completions() 调用 + 文本约定来模拟工具调用，兼容任何只接受
        标准 messages 列表（role: system/user/assistant）的客户端实现。
        """
        system_message = dict(self.prompts["system_message"])
        system_message["content"] = system_message["content"] + _TEXT_PROTOCOL_INSTRUCTIONS
        messages: List[Dict[str, Any]] = [
            system_message,
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]

        for round_idx in range(self.max_tool_rounds):
            content = self.client.completions(messages) or ""
            tool_call = self._parse_text_tool_call(content)
            if tool_call is None:
                return content

            logger.info(f"AI审查请求调用工具 (文本协议, 第{round_idx + 1}轮): {tool_call['name']}")
            messages.append({"role": "assistant", "content": content})
            result_text = self._dispatch_tool(tool_call)
            messages.append({
                "role": "user",
                "content": f"工具 {tool_call['name']} 返回结果：\n{result_text}\n\n"
                           f"请继续审查；如已获得足够信息，请直接输出最终审查报告（不要再输出 tool_call）。",
            })

        logger.warning(f"AI审查(文本协议)已达到最大工具调用轮数({self.max_tool_rounds})，强制要求给出最终结论")
        messages.append({
            "role": "user",
            "content": "已达到本次审查的最大工具调用次数，请直接给出最终审查报告，不要再输出 tool_call。",
        })
        return self.client.completions(messages) or ""

    @staticmethod
    def _parse_text_tool_call(content: str) -> Optional[Dict[str, Any]]:
        """
        尝试把纯文本回复解析为工具调用请求。返回 {"name","arguments"}；
        如果不是工具调用（即应作为最终审查报告直接返回），返回 None。
        """
        if not content:
            return None
        text = content.strip()
        # 去掉可能的 markdown 代码块包裹（```json ... ``` 或 ``` ... ```）
        fence_match = re.match(r'^```(?:json)?\s*(.*?)\s*```$', text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()
        if not text.startswith('{') or '"tool_call"' not in text:
            return None
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        tool_call = parsed.get('tool_call') if isinstance(parsed, dict) else None
        if not isinstance(tool_call, dict) or not tool_call.get('name'):
            return None
        return {"name": tool_call.get('name'), "arguments": tool_call.get('arguments') or {}}

    def _dispatch_tool(self, call: Dict[str, Any]) -> str:
        """执行单个工具调用；任何异常/未知工具都返回可读的错误文本给模型，而不是抛异常中断整个审查。"""
        name = call.get("name")
        arguments = call.get("arguments") or {}
        handler = self.tool_context.get(name)
        if handler is None:
            return f"错误: 未知或不可用的工具 '{name}'"
        try:
            if name == "read_file":
                return handler(arguments.get("file_path", "")) or "文件内容为空"
            elif name == "search_code":
                return handler(arguments.get("query", ""), arguments.get("max_results", 20)) or "未找到匹配结果"
            return f"错误: 未实现的工具 '{name}'"
        except Exception as e:
            logger.warning(f"工具调用执行失败 ({name}): {e}")
            return f"错误: 工具执行失败 - {e}"
