import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse

import requests

from biz.utils.log import logger
from biz.utils.default_config import get_env_bool, get_env_with_default


class DingTalkNotifier:
    def __init__(self, webhook_url=None):
        self.enabled = get_env_bool('DINGTALK_ENABLED')
        self.default_webhook_url = webhook_url or get_env_with_default('DINGTALK_WEBHOOK_URL')

    def _get_webhook_url(self, project_name=None, url_slug=None):
        """
        获取项目对应的 Webhook URL
        :param project_name: 项目名称
        :param url_slug: 由 gitlab 项目的 url 转换而来的 slug
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称，且未设置默认的钉钉 Webhook URL。")

        # 构造目标键
        target_key_project = f"DINGTALK_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"DINGTALK_WEBHOOK_URL_{url_slug.upper()}" if url_slug else None

        # 遍历环境变量
        for env_key, env_value in os.environ.items():
            env_key_upper = env_key.upper()
            if env_key_upper == target_key_project:
                logger.info(f"钉钉推送地址匹配：项目级键 {env_key}")
                return env_value  # 找到项目名称对应的 Webhook URL，直接返回
            if target_key_url_slug and env_key_upper == target_key_url_slug:
                logger.info(f"钉钉推送地址匹配：线级键 {env_key}")
                return env_value  # 找到 GitLab URL 对应的 Webhook URL，直接返回

        # 如果未找到匹配的环境变量，降级使用全局的 Webhook URL
        if self.default_webhook_url:
            logger.info(f"钉钉推送地址匹配：未找到定制键（project={project_name}, slug={url_slug}），回退默认地址")
            return self.default_webhook_url

        # 如果既未找到匹配项，也没有默认值，抛出异常
        raise ValueError(f"未找到项目 '{project_name}' 对应的钉钉Webhook URL，且未设置默认的 Webhook URL。")

    def send_message(self, content: str, msg_type='text', title='通知', is_at_all=False, project_name=None, url_slug=None):
        if not self.enabled:
            logger.info("钉钉推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
            # 钉钉自定义机器人消息内容最大 20000 字节（text / markdown 类型均适用）
            # 注意：中文按 UTF-8 编码占 3 字节，约 6600 个中文字符即可能触达上限
            # https://open.dingtalk.com/document/robots/custom-robot-access
            MAX_CONTENT_BYTES = 20000
            content_length = len(content.encode('utf-8'))

            if content_length <= MAX_CONTENT_BYTES:
                # 内容在限制范围内，直接发送
                message = self._build_message(content, title, msg_type, is_at_all)
                self._send_message(post_url, message)
            else:
                # 内容超过限制，分割发送，避免触发钉钉 body 大小限制
                logger.warning(f"钉钉消息内容超过{MAX_CONTENT_BYTES}字节限制，将分割发送。总长度: {content_length}字节")
                self._send_message_in_chunks(content, title, post_url, msg_type, is_at_all, MAX_CONTENT_BYTES)
        except Exception as e:
            logger.error(f"钉钉消息发送失败! 错误信息: {str(e)}")

    def _build_message(self, content, title, msg_type, is_at_all):
        """构造钉钉消息体"""
        if msg_type == 'markdown':
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content
                },
                "at": {
                    "isAtAll": is_at_all
                }
            }
        return {
            "msgtype": "text",
            "text": {
                "content": content
            },
            "at": {
                "isAtAll": is_at_all
            }
        }

    def _send_message(self, post_url, message, chunk_num=None, total_chunks=None):
        """发送请求并处理响应"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Charset": "UTF-8"
            }
            response = requests.post(url=post_url, data=json.dumps(message), headers=headers)
            response_data = response.json()
            suffix = f", 第{chunk_num}/{total_chunks}部分" if chunk_num else ""
            if response_data.get('errmsg') == 'ok':
                logger.info(f"钉钉消息{'分块' if chunk_num else ''}发送成功! webhook_url:{post_url}{suffix}")
            else:
                logger.error(
                    f"钉钉消息{'分块' if chunk_num else ''}发送失败! webhook_url:{post_url},errmsg:{response_data.get('errmsg')}{suffix}")
        except Exception as e:
            logger.error(f"钉钉消息{'分块' if chunk_num else ''}发送失败! 错误信息: {str(e)}")

    def _send_message_in_chunks(self, content, title, post_url, msg_type, is_at_all, max_bytes):
        """将内容分割成多个部分并分别发送"""
        chunks = self._split_content(content, max_bytes)
        for i, chunk in enumerate(chunks):
            chunk_title = f"{title} (第{i + 1}/{len(chunks)}部分)" if title else f"通知 (第{i + 1}/{len(chunks)}部分)"
            message = self._build_message(chunk, chunk_title, msg_type, is_at_all)
            self._send_message(post_url, message, chunk_num=i + 1, total_chunks=len(chunks))
            if i < len(chunks) - 1:
                # 钉钉机器人限频 20 条/分钟，分块之间稍作间隔避免触发限频
                time.sleep(1)

    def _split_content(self, content, max_bytes):
        """
        将内容按最大字节长度分割成多个部分
        优先在换行处切割避免断行；单段无换行时按字节边界强制切割，避免死循环
        """
        chunks = []
        content_bytes = content.encode('utf-8')
        content_length = len(content_bytes)
        start_pos = 0

        while start_pos < content_length:
            end_pos = start_pos + max_bytes
            if end_pos >= content_length:
                chunks.append(content_bytes[start_pos:].decode('utf-8', errors='ignore'))
                break

            # 优先向前找最近的换行符，避免在行中间断开
            cut_pos = end_pos
            while cut_pos > start_pos and content_bytes[cut_pos - 1:cut_pos] != b'\n':
                cut_pos -= 1
            # 该段内没有换行符时，按字节截断（向前调整到多字节字符边界，避免切断中文字符）
            if cut_pos == start_pos:
                cut_pos = end_pos
                while cut_pos > start_pos and (content_bytes[cut_pos] & 0xC0) == 0x80:
                    cut_pos -= 1

            chunk = content_bytes[start_pos:cut_pos].decode('utf-8', errors='ignore')
            chunks.append(chunk)
            start_pos = cut_pos

        return chunks
