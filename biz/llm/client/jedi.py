import os
import json
import time
import requests
from typing import Any, Dict, List, Optional

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger
from biz.utils.default_config import get_env_with_default, get_env_int

# 输出侧 max_tokens 的硬上限。REVIEW_MAX_TOKENS 本意是"送进模型的 diff 输入预算"，
# 本客户端复用它作为 completion 的 max_tokens，若用户把它调到很大（如 10 万）会超出
# 模型的单次输出上限、被网关直接拒绝，因此统一收敛到这个值。
MAX_COMPLETION_TOKENS = 16000


class JediClient(BaseClient):
    # 已用真实凭证实测（2026-07-29，official-deepseek-v4-pro）：Jedi网关基于LangChain封装，
    # 传tools/tool_choice参数后模型会把finish_reason改成"tool_calls"，但网关返回的是不完整的
    # AIMessageChunk（type=AIMessageChunk），实际tool_calls字段始终为空，无法提取到真正的工具调用参数。
    # 更关键的是：即使完全不传tools（普通completions()），只要模型自己"想"调用什么东西（比如
    # 提示词里出现"搜索/确认"等语义），也会触发同样的finish_reason=tool_calls+内容截断在"思考过程"
    # 处，说明这是模型/网关自身的原生工具调用倾向在作怪，而不是我们传参导致的。
    # 结论：native function calling 对这个网关当前不可用，保持False，走 AgenticCodeReviewer 的
    # 纯文本协议模拟路径（已实测在明确指令下可以正确输出约定的tool_call JSON）。
    # completions_with_tools() 予以保留：如果之后网关修复了这个问题，只需把这里改回 True 验证即可。
    supports_tools = False

    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("JEDI_API_KEY")
        self.base_url = get_env_with_default("JEDI_API_BASE_URL")
        self.default_model = get_env_with_default("JEDI_API_MODEL")
        self.thinking_level = (get_env_with_default("JEDI_THINKING_LEVEL") or "high").lower().strip()
        self.context_window = get_env_int("JEDI_CONTEXT_WINDOW", 65536)
        
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")
        if not self.base_url:
            raise ValueError("Base URL is required. Please provide it or set it in the environment variables.")

    def _thinking_temperature(self) -> float:
        """思考程度 → temperature 档位（仅 Jedi 因无原生思考参数，用温度小幅递增模拟思考强度）。

        审查场景已收敛幅度：off/low 保持低温 0.2，medium 0.3，max 仅 0.5，
        避免高温破坏审查输出的确定性。"""
        temp_map = {"off": 0.2, "low": 0.2, "medium": 0.3, "high": 0.4, "max": 0.5}
        return temp_map.get(self.thinking_level, 0.2)

    def _convert_messages_to_jedi_format(self, messages: List[Dict[str, str]]) -> Dict:
        """Convert OpenAI format messages to Jedi format"""
        user_messages = []
        system_message = ""
        chat_history = []
        
        for i, message in enumerate(messages):
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "system":
                system_message = content
            elif role == "user":
                # 最后一条用户消息作为当前输入
                if i == len(messages) - 1:
                    user_messages.append({
                        "text": content,
                        "type": "text"
                    })
                else:
                    # 之前的消息加入历史记录
                    chat_history.append(["user", content])
            elif role == "assistant":
                chat_history.append(["ai", content])
        
        return {
            "user": user_messages,
            "system": system_message,
            "chat_history": chat_history
        }

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        try:
            model = model or self.default_model
            logger.debug(f"Sending request to Jedi API. Model: {model}, Messages: {messages}")
            
            # 转换消息格式
            jedi_input = self._convert_messages_to_jedi_format(messages)
            
            # 根据请求复杂度动态调整参数
            total_content_length = sum(len(str(msg.get("content", ""))) for msg in messages)
            
            # 获取系统配置的最大 token 限制
            # 注意：REVIEW_MAX_TOKENS 语义是"送进模型的 diff 输入预算"，这里复用作输出 max_tokens，
            # 因此必须再套一层输出上限，否则把它调大（如 10 万）会导致网关拒绝请求。
            # 同时用模型上下文窗口兜底，保证不超出模型能力。
            system_max_tokens = min(get_env_int("REVIEW_MAX_TOKENS", 10000), self.context_window, MAX_COMPLETION_TOKENS)
            
            # 配置：初始超时600秒，最多重试2次，每次重试超时加倍
            timeout = 600
            max_retries = 1
            
            # 根据内容长度判断复杂度并调整参数，但不能超过系统限制
            if total_content_length < 400:  # 简单请求
                max_tokens = min(4000, system_max_tokens)
                complexity_level = "simple"
            elif total_content_length < 1000:  # 中等复杂度
                max_tokens = min(10000, system_max_tokens)
                complexity_level = "medium"
            else:  # 复杂请求
                max_tokens = system_max_tokens
                complexity_level = "complex"
                
            logger.info(f"请求复杂度: {complexity_level}, 内容长度: {total_content_length}, 最大tokens: {max_tokens}, 系统限制: {system_max_tokens}, 超时: {timeout}秒, 最大重试: {max_retries}次")
            
            # 构建请求体
            payload = {
                "input": jedi_input,
                "model_name": model,
                "chatModelConfig": {
                    "temperature": self._thinking_temperature(),
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0,
                    "max_tokens": max_tokens,
                    "top_p": 1,
                    "seed": 42
                },
                "stream": False
            }
            
            # 设置请求头
            headers = {
                "accept": "application/json",
                "token": self.api_key,
                "Content-Type": "application/json"
            }
            
            # 实现重试机制（初始超时600秒，最多重试2次，每次重试超时加倍，最大1200秒）
            for attempt in range(max_retries + 1):
                current_timeout = min(timeout * (2 ** attempt), 1200)
                try:
                    logger.info(f"Jedi API 请求尝试 {attempt + 1}/{max_retries + 1}, 复杂度: {complexity_level}, 超时设置: {current_timeout}秒")
                    
                    # 发送请求
                    response = requests.post(
                        self.base_url,
                        headers=headers,
                        json=payload,
                        timeout=current_timeout
                    )
                    
                    logger.debug(f"Jedi API response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(result)
                        # 根据实际响应格式解析结果
                        if isinstance(result, dict):
                            # 检测"思考过程被截断"的异常响应：实测发现该模型/网关在内容语义触发其
                            # 内置的工具调用倾向时（无论我们是否主动传了tools参数），可能只返回不完整的
                            # AIMessageChunk —— finish_reason=tool_calls，但没有任何真实的tool_calls数据，
                            # content也只是半截的思考文字。这种响应不能当作正常结果返回，否则会破坏输出
                            # 格式（比如缺少"总分:XX分"导致评分解析失败），这里当作失败处理并复用现有重试逻辑。
                            response_metadata = result.get("response_metadata") or {}
                            finish_reason = response_metadata.get("finish_reason")
                            has_real_tool_calls = bool(result.get("tool_calls") or result.get("toolCalls"))
                            if finish_reason == "tool_calls" and not has_real_tool_calls:
                                logger.warning(
                                    f"Jedi API 返回了不完整的响应(finish_reason=tool_calls但无真实tool_calls数据，"
                                    f"疑似模型内置工具调用倾向被触发导致内容截断)，尝试 {attempt + 1}/{max_retries + 1}"
                                )
                                if attempt == max_retries:
                                    error_result = f"❌ AI审查失败: 响应内容不完整\n\n详细信息:\n- 错误类型: 疑似模型触发内置工具调用倾向导致响应被截断 (finish_reason=tool_calls)\n- 建议: 请查看日志中的完整响应内容，或调整prompt措辞后重试\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- 超时设置: {current_timeout}秒"
                                    logger.error(error_result)
                                    return error_result
                                continue

                            # 假设响应格式包含 content 或 message 字段
                            content = result.get("content") or result.get("message") or result.get("output", "")
                            if isinstance(content, dict):
                                content = content.get("text", "") or content.get("content", "")
                            
                            if content and str(content).strip():
                                logger.info(f"Jedi API 请求成功，用时: 尝试 {attempt + 1}")
                                return str(content)
                            else:
                                logger.warning("Jedi API 返回空内容")
                                if attempt == max_retries:
                                    error_result = f"❌ AI审查失败: API返回空内容\n\n详细信息:\n- 状态码: 200\n- 响应内容: {str(result)[:500]}\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- 超时设置: {current_timeout}秒"
                                    logger.error(error_result)
                                    return error_result
                                continue
                        else:
                            content = str(result) if result else ""
                            if content.strip():
                                return content
                            else:
                                if attempt == max_retries:
                                    error_result = f"❌ AI审查失败: API返回空内容\n\n详细信息:\n- 状态码: 200\n- 响应类型: {type(result)}\n- 响应内容: {str(result)[:500]}\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- 超时设置: {current_timeout}秒"
                                    logger.error(error_result)
                                    return error_result
                                continue
                    else:
                        error_msg = f"Jedi API请求失败，状态码: {response.status_code}"
                        try:
                            error_detail = response.json()
                            error_msg += f", 错误详情: {error_detail}"
                        except:
                            error_msg += f", 响应内容: {response.text[:200]}"
                        
                        logger.error(error_msg)
                        
                        # 根据状态码返回详细的错误信息
                        if response.status_code == 401:
                            error_result = f"❌ AI审查失败: API认证失败\n\n详细信息:\n- 错误类型: 认证失败 (401 Unauthorized)\n- 可能原因: API密钥不正确或已过期\n- 建议: 请检查JEDI_API_KEY环境变量配置\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- API地址: {self.base_url}"
                            logger.error(error_result)
                            return error_result
                        elif response.status_code == 404:
                            error_result = f"❌ AI审查失败: API接口未找到\n\n详细信息:\n- 错误类型: 接口不存在 (404 Not Found)\n- 可能原因: API地址不正确或接口已变更\n- 建议: 请检查JEDI_API_BASE_URL环境变量配置\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- API地址: {self.base_url}"
                            logger.error(error_result)
                            return error_result
                        elif response.status_code == 429:
                            if attempt < max_retries:
                                # 固定等待5秒后重试
                                wait_time = 5
                                logger.info(f"API 限流，等待 {wait_time} 秒后重试...")
                                time.sleep(wait_time)
                                continue
                            error_result = f"❌ AI审查失败: API请求限流\n\n详细信息:\n- 错误类型: 请求过于频繁 (429 Too Many Requests)\n- 可能原因: 超过API调用频率限制\n- 建议: 请稍后重试或联系管理员增加配额\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- API地址: {self.base_url}"
                            logger.error(error_result)
                            return error_result
                        else:
                            if attempt == max_retries:
                                error_result = f"❌ AI审查失败: API请求错误\n\n详细信息:\n{error_msg}\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- 超时设置: {current_timeout}秒\n- API地址: {self.base_url}"
                                logger.error(error_result)
                                return error_result
                            continue
                            
                except requests.exceptions.Timeout:
                    logger.warning(f"Jedi API请求超时 (尝试 {attempt + 1}/{max_retries + 1}, 超时: {current_timeout}秒)")
                    if attempt == max_retries:
                        error_result = f"❌ AI审查失败: 请求超时\n\n详细信息:\n- 错误类型: 请求超时 (Timeout)\n- 超时设置: {current_timeout}秒\n- 可能原因: 网络延迟过高或服务器响应缓慢\n- 建议: 请检查网络连接或稍后重试\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- API地址: {self.base_url}\n- 复杂度: {complexity_level}\n- 内容长度: {total_content_length}"
                        logger.error(error_result)
                        return error_result
                    # 继续下一次重试
                    continue
                    
                except requests.exceptions.ConnectionError:
                    logger.warning(f"无法连接到Jedi API (尝试 {attempt + 1}/{max_retries + 1})")
                    if attempt == max_retries:
                        error_result = f"❌ AI审查失败: 无法连接到API\n\n详细信息:\n- 错误类型: 连接错误 (Connection Error)\n- 可能原因: 网络不可达、DNS解析失败或服务器未启动\n- 建议: 请检查网络连接和API服务状态\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- API地址: {self.base_url}"
                        logger.error(error_result)
                        return error_result
                    # 固定等待5秒后重试
                    wait_time = 5
                    time.sleep(wait_time)
                    continue
                    
        except Exception as e:
            error_result = f"❌ AI审查失败: 未知错误\n\n详细信息:\n- 错误类型: {type(e).__name__}\n- 错误消息: {str(e)}\n- 建议: 请查看日志获取更多信息或联系管理员\n- API地址: {self.base_url}"
            logger.error(f"Jedi API error: {str(e)}", exc_info=True)
            return error_result

    def completions_with_tools(self,
                                messages: List[Dict[str, Any]],
                                tools: List[Dict[str, Any]],
                                model: Optional[str] | NotGiven = NOT_GIVEN,
                                ) -> Dict[str, Any]:
        """
        实验性：尝试让 Jedi 网关按 OpenAI 风格识别 tools/tool_choice 参数并返回 tool_calls。
        Jedi 网关的真实 API 契约未经官方文档确认，这里只是按用户要求先尝试性发送，
        通过运行日志观察网关的真实响应（是否识别了tools、是否返回了tool_calls）来验证。

        无论网关是否真的支持，本方法都不会让审查流程失败：
        - 网关如果不识别 tools/tool_choice，通常会直接忽略这两个多余字段，正常返回文本内容，
          此时 tool_calls 为空列表，AgenticCodeReviewer 会把内容当作最终审查报告直接使用。
        - 如果请求本身出错（非200/网络异常/返回内容为空），会自动降级为调用普通的 completions()
          （复用其完整的重试/超时/错误处理逻辑），保证至少能拿到一次正常审查结果。
        """
        model = model or self.default_model
        try:
            jedi_input = self._convert_messages_to_jedi_format(messages)
            payload = {
                "input": jedi_input,
                "model_name": model,
                "chatModelConfig": {
                    "temperature": self._thinking_temperature(),
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0,
                    "max_tokens": min(get_env_int("REVIEW_MAX_TOKENS", 10000), self.context_window, MAX_COMPLETION_TOKENS),
                    "top_p": 1,
                    "seed": 42
                },
                # 实验性字段：仿照 OpenAI function calling 的顶层参数写法
                "tools": tools,
                "tool_choice": "auto",
                "stream": False
            }
            headers = {
                "accept": "application/json",
                "token": self.api_key,
                "Content-Type": "application/json"
            }
            logger.info(f"Jedi API (实验性tools请求) 发送，工具数: {len(tools)}")
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=600)
            logger.debug(f"Jedi API (实验性tools请求) response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Jedi API (实验性tools请求) 响应: {result}")
                tool_calls = self._extract_tool_calls(result)
                content = self._extract_content_from_result(result)
                if tool_calls:
                    logger.info(f"Jedi网关返回了 {len(tool_calls)} 个tool_calls，说明该网关/模型支持工具调用")
                elif content:
                    logger.info("Jedi网关返回了正常文本内容但没有tool_calls，可能网关忽略了tools字段（或本轮无需调用工具）")
                if content or tool_calls:
                    assistant_message: Dict[str, Any] = {"role": "assistant", "content": content or ""}
                    if tool_calls:
                        assistant_message["tool_calls"] = [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                                },
                            }
                            for tc in tool_calls
                        ]
                    return {"content": content, "tool_calls": tool_calls, "assistant_message": assistant_message}
                logger.warning("Jedi API (实验性tools请求) 返回空内容，降级为普通completions")
            else:
                logger.warning(f"Jedi API (实验性tools请求) 返回状态码 {response.status_code}，"
                               f"可能网关不识别tools参数，降级为普通completions。响应: {response.text[:300]}")
        except Exception as e:
            logger.warning(f"Jedi API (实验性tools请求) 异常: {e}，降级为普通completions", exc_info=True)

        # 降级：走原有稳健的 completions()（含完整重试/超时/错误处理逻辑）
        content = self.completions(messages, model=model)
        return {"content": content, "tool_calls": [], "assistant_message": {"role": "assistant", "content": content}}

    @staticmethod
    def _extract_content_from_result(result) -> str:
        """从Jedi网关响应中提取文本内容，与completions()里的解析逻辑保持一致。"""
        if isinstance(result, dict):
            content = result.get("content") or result.get("message") or result.get("output", "")
            if isinstance(content, dict):
                content = content.get("text", "") or content.get("content", "")
            return str(content) if content else ""
        return str(result) if result else ""

    @staticmethod
    def _extract_tool_calls(result) -> List[Dict[str, Any]]:
        """
        尝试从Jedi网关响应中提取工具调用（实验性，字段名未经官方文档确认，
        兼容几种常见的命名方式：tool_calls/toolCalls，可能在顶层或message/output对象内）。
        解析不到就返回空列表，不抛异常。
        """
        if not isinstance(result, dict):
            return []
        raw_calls = None
        for key in ("tool_calls", "toolCalls"):
            if result.get(key):
                raw_calls = result[key]
                break
        if raw_calls is None:
            for container_key in ("message", "output"):
                container = result.get(container_key)
                if isinstance(container, dict):
                    for key in ("tool_calls", "toolCalls"):
                        if container.get(key):
                            raw_calls = container[key]
                            break
                if raw_calls:
                    break
        if not raw_calls or not isinstance(raw_calls, list):
            return []

        tool_calls = []
        for i, tc in enumerate(raw_calls):
            if not isinstance(tc, dict):
                continue
            func = tc.get("function", tc)  # 兼容 {"function": {"name":,"arguments":}} 或直接 {"name":,"arguments":}
            name = func.get("name")
            if not name:
                continue
            raw_args = func.get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args) if raw_args else {}
                except (json.JSONDecodeError, TypeError):
                    arguments = {}
            elif isinstance(raw_args, dict):
                arguments = raw_args
            else:
                arguments = {}
            tool_calls.append({"id": tc.get("id", f"jedi-tool-{i}"), "name": name, "arguments": arguments})
        return tool_calls
