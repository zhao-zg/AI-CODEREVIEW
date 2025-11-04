import os
import json
import time
import requests
from typing import Dict, List, Optional

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger
from biz.utils.default_config import get_env_with_default, get_env_int


class JediClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_with_default("JEDI_API_KEY")
        self.base_url = get_env_with_default("JEDI_API_BASE_URL")
        self.default_model = get_env_with_default("JEDI_API_MODEL")
        
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")
        if not self.base_url:
            raise ValueError("Base URL is required. Please provide it or set it in the environment variables.")

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
            system_max_tokens = get_env_int("REVIEW_MAX_TOKENS", 10000)
            
            # 固定配置：超时600秒，只重试1次
            timeout = 600
            max_retries = 1
            
            # 根据内容长度判断复杂度并调整参数，但不能超过系统限制
            if total_content_length < 400:  # 简单请求
                max_tokens = min(4000, system_max_tokens)
                thinking = False
                complexity_level = "simple"
            elif total_content_length < 1000:  # 中等复杂度
                max_tokens = min(10000, system_max_tokens)
                thinking = False
                complexity_level = "medium"
            else:  # 复杂请求
                max_tokens = system_max_tokens
                thinking = True
                complexity_level = "complex"
                
            logger.info(f"请求复杂度: {complexity_level}, 内容长度: {total_content_length}, 最大tokens: {max_tokens}, 系统限制: {system_max_tokens}, 超时: {timeout}秒, 最大重试: {max_retries}次")
            
            # 构建请求体
            payload = {
                "input": jedi_input,
                "model_name": model,
                "chatModelConfig": {
                    "temperature": 0.2,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0,
                    "max_tokens": max_tokens,
                    "top_p": 1,
                    "seed": 42,
                    "thinking": thinking
                },
                "stream": False
            }
            
            # 设置请求头
            headers = {
                "accept": "application/json",
                "token": self.api_key,
                "Content-Type": "application/json"
            }
            
            # 实现重试机制（固定超时600秒，只重试1次）
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Jedi API 请求尝试 {attempt + 1}/{max_retries + 1}, 复杂度: {complexity_level}, 超时设置: {timeout}秒")
                    
                    # 发送请求
                    response = requests.post(
                        self.base_url,
                        headers=headers,
                        json=payload,
                        timeout=timeout
                    )
                    
                    logger.debug(f"Jedi API response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(result)
                        # 根据实际响应格式解析结果
                        if isinstance(result, dict):
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
                                    error_result = f"❌ AI审查失败: API返回空内容\n\n详细信息:\n- 状态码: 200\n- 响应内容: {str(result)[:500]}\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- 超时设置: {timeout}秒"
                                    logger.error(error_result)
                                    return error_result
                                continue
                        else:
                            content = str(result) if result else ""
                            if content.strip():
                                return content
                            else:
                                if attempt == max_retries:
                                    error_result = f"❌ AI审查失败: API返回空内容\n\n详细信息:\n- 状态码: 200\n- 响应类型: {type(result)}\n- 响应内容: {str(result)[:500]}\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- 超时设置: {timeout}秒"
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
                                error_result = f"❌ AI审查失败: API请求错误\n\n详细信息:\n{error_msg}\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- 超时设置: {timeout}秒\n- API地址: {self.base_url}"
                                logger.error(error_result)
                                return error_result
                            continue
                            
                except requests.exceptions.Timeout:
                    logger.warning(f"Jedi API请求超时 (尝试 {attempt + 1}/{max_retries + 1}, 超时: {timeout}秒)")
                    if attempt == max_retries:
                        error_result = f"❌ AI审查失败: 请求超时\n\n详细信息:\n- 错误类型: 请求超时 (Timeout)\n- 超时设置: {timeout}秒\n- 可能原因: 网络延迟过高或服务器响应缓慢\n- 建议: 请检查网络连接或稍后重试\n- 尝试次数: {attempt + 1}/{max_retries + 1}\n- API地址: {self.base_url}\n- 复杂度: {complexity_level}\n- 内容长度: {total_content_length}"
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
