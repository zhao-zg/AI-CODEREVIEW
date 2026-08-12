import abc
import json
import os
import re
from typing import Dict, Any, List, Tuple

import yaml
from jinja2 import Template

from biz.llm.factory import Factory
from biz.utils.log import logger
from biz.utils.token_util import count_tokens, truncate_text_by_tokens
from biz.utils.default_config import get_env_with_default, get_env_int, get_review_input_budget


def is_api_error_message(text: str) -> bool:
    """
    检测文本是否是API错误消息，而不是正常的代码审查结果
    
    Args:
        text: 待检测的文本
        
    Returns:
        bool: True表示是错误消息，False表示是正常审查结果
    """
    if not text or not isinstance(text, str):
        return True
    
    # 首先检查是否过短（但增加更智能的判断）
    text_stripped = text.strip()
    if len(text_stripped) < 15:  # 非常短的消息很可能是错误
        logger.warning(f"检测到过短的响应，可能是错误消息: {text}")
        return True
    if len(text_stripped) > 200:
        return False  # 假设超过200字符的消息通常是正常的审查结果
    # 定义API错误消息的特征模式
    error_patterns = [
        # 超时相关
        r"请求超时",
        r"(?<!\w)timeout(?!\w)",  # 避免匹配 timeout参数 等正常文本
        r"timed.*out",
        r"请稍后重试",
        r"稍后重试",
        r"(?<!配置)超时(?!配置|参数|机制|处理)",  # 避免匹配"超时配置"等正常文本
        r"time.*out",
        r"read.*timeout",
        r"connect.*timeout",
        
        # 连接错误（更精确的模式）
        r"无法连接(?!池)",  # 避免匹配"连接池"
        r"连接失败",
        r"网络连接(?!异常处理|重试)",  # 避免匹配正常的技术讨论
        r"connection.*error",
        r"connection.*failed",
        r"network.*error",
        r"socket.*error",
        
        # API错误
        r"API.*出错",
        r"API.*失败",
        r"API.*错误",
        r"API.*超时",
        r"认证失败",
        r"接口未找到",
        r"服务返回为空",
        r"服务不可用",
        r"service.*unavailable",
        
        # HTTP状态码错误
        r"状态码.*40[0-9]",
        r"状态码.*50[0-9]",
        r"http.*error",
        r"status.*code.*[45][0-9][0-9]",
        
        # 其他技术错误
        r"调用.*时出错",
        r"请检查.*配置",
        r"请检查.*密钥",
        r"请检查.*地址",
        r"服务器.*错误",
        r"server.*error",
        r"内部错误",
        r"internal.*error",
        
        # 明确的错误指示词
        r"^错误[:：]",
        r"^失败[:：]",
        r"^异常[:：]",
        r"^Error[:：]",
    ]
    
    # 检查是否匹配任何错误模式
    text_lower = text.lower()
    for pattern in error_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(f"检测到API错误消息: {text[:100]}...")
            return True
    
    # 额外检查：如果是较短的消息（15-50字符）且不包含常见的审查关键词，可能是错误
    if len(text_stripped) < 50:
        # 常见的正常审查关键词
        normal_keywords = [
            '代码', '审查', '建议', '优化', '质量', '规范', '改进', '修复', '提交',
            'code', 'review', 'suggest', 'recommend', 'quality', 'improve', 'fix',
            '总分', '评分', '分数', 'score', 'point',
            '良好', '不错', '清晰', 'good', 'clear', 'clean'
        ]
        
        has_normal_keywords = any(keyword in text_lower for keyword in normal_keywords)
        if not has_normal_keywords:
            logger.warning(f"检测到可疑的短消息，缺少审查关键词: {text}")
            return True
    
    return False


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self, prompt_key: str):
        self.client = Factory().getClient()
        self.prompts = self._load_prompts(prompt_key, get_env_with_default("REVIEW_STYLE"))

    def _load_prompts(self, prompt_key: str, style="professional") -> Dict[str, Any]:
        """加载提示词配置"""
        prompt_templates_file = "conf/prompt_templates.yml"
        try:
            # 在打开 YAML 文件时显式指定编码为 UTF-8，避免使用系统默认的 GBK 编码。
            with open(prompt_templates_file, "r", encoding="utf-8") as file:
                full_config = yaml.safe_load(file)
                if not isinstance(full_config, dict):
                    raise ValueError(f"配置文件格式错误，期望YAML字典，实际: {type(full_config).__name__}")

                prompts = full_config.get(prompt_key)
                if prompts is None:
                    # 尝试从模板文件兜底
                    template_file = "conf_templates/prompt_templates.yml"
                    if os.path.exists(template_file):
                        with open(template_file, "r", encoding="utf-8") as tf:
                            tmpl_config = yaml.safe_load(tf)
                            if isinstance(tmpl_config, dict) and prompt_key in tmpl_config:
                                prompts = tmpl_config[prompt_key]
                                logger.info(f"'{prompt_key}' 从模板文件 conf_templates/prompt_templates.yml 自动加载（当前配置文件缺少此 key）")
                    if prompts is None:
                        raise KeyError(f"配置文件中未找到 '{prompt_key}'，可用的key: {list(full_config.keys())}")

                if not isinstance(prompts, dict):
                    raise ValueError(f"'{prompt_key}' 的值不是字典，实际: {type(prompts).__name__}")

                if 'system_prompt' not in prompts:
                    raise KeyError(f"'{prompt_key}' 缺少 system_prompt 字段")
                if 'user_prompt' not in prompts:
                    raise KeyError(f"'{prompt_key}' 缺少 user_prompt 字段")

                # 使用Jinja2渲染模板
                def render_template(template_str: str) -> str:
                    return Template(template_str).render(style=style)

                system_prompt = render_template(prompts["system_prompt"])
                user_prompt = render_template(prompts["user_prompt"])

                return {
                    "system_message": {"role": "system", "content": system_prompt},
                    "user_message": {"role": "user", "content": user_prompt},
                }
        except (FileNotFoundError, KeyError, ValueError, yaml.YAMLError) as e:
            logger.error(f"加载提示词配置失败 (key={prompt_key}): {e}")
            raise Exception(f"提示词配置加载失败: {e}")

    def call_llm(self, messages: List[Dict[str, Any]]) -> str:
        """调用 LLM 进行代码审核"""
        logger.info(f"向 AI 发送代码 Review 请求, messages: {messages}")
        review_result = self.client.completions(messages=messages)
        logger.info(f"收到 AI 返回结果: {review_result}")
        return review_result

    @abc.abstractmethod
    def review_code(self, *args, **kwargs) -> str:
        """抽象方法，子类必须实现"""
        pass


class CodeReviewer(BaseReviewer):
    """代码 Diff 级别的审查"""

    def __init__(self):
        super().__init__("code_review_prompt")

    def review_and_strip_code(self, changes_text: str, commits_text: str = "") -> str:
        """
        Review判断changes_text超出取前 get_review_input_budget() 个token（自动按上下文窗口30%），
        超出则截断changes_text，调用review_code方法，返回review_result，如果review_result是markdown格式，则去掉头尾的```
        :param changes_text:
        :param commits_text:        :return:
        """
        # 如果超长，取前 get_review_input_budget() 个token（自动按上下文窗口30%）
        review_max_tokens = get_review_input_budget()
        # 如果changes为空,打印日志
        if not changes_text:
            logger.info("代码为空, diffs_text = %", str(changes_text))
            return "代码为空"

        # 计算tokens数量，如果超过预算，截断changes_text
        tokens_count = count_tokens(changes_text)
        if tokens_count > review_max_tokens :
            changes_text = truncate_text_by_tokens(changes_text, review_max_tokens)
        logger.debug(f"Reviewing code with {tokens_count} tokens, truncated to {len(changes_text)} characters if necessary.")
        logger.debug(f"commits_text with {commits_text} ")

        # 调用review_code方法
        review_result = self.review_code(changes_text, commits_text).strip()
        # 检查是否是API错误消息
        if is_api_error_message(review_result):
            logger.error(f"检测到API错误，返回错误消息: {review_result[:100]}...")
            return review_result  # 返回错误消息，由调用方决定是否发布到评论
        
        # 验证审查结果
        if not review_result:
            logger.warning("AI返回的审查结果为空")
            return None  # 返回None表示应该跳过写入
            
        if review_result.startswith("```markdown") and review_result.endswith("```"):
            return review_result[11:-3].strip()
        return review_result

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """Review 代码并返回结果"""
        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分（支持多种评分格式）"""
        if not review_text:
            return 0
        
        # 匹配多种评分格式（按优先级排列）。
        # 数值两侧兼容 AI 常见的 markdown 加粗/反引号包裹（如 "总分: **85分**"、
        # "`评分: 85分`"），否则解析不到会按 0 分处理（Excel 审查曾因 AI 输出
        # "文件评估: **82分**" 而把 82 分误计为 0 分）。
        _num = r"\s*[*`]{0,2}\s*(\d+)\s*[*`]{0,2}\s*"
        score_patterns = [
            r"总分[:：]" + _num + r"分?",          # 总分：85分 或 总分: 85
            r"总得分[:：]" + _num + r"分?",        # 总得分：85分
            r"综合评分[:：]" + _num + r"分?",      # 综合评分：85分
            r"最终得分[:：]" + _num + r"分?",      # 最终得分：85分
            r"评分[:：]" + _num + r"分?",          # 评分：85分
            r"得分[:：]" + _num + r"分?",          # 得分：85分
            r"分数[:：]" + _num + r"分?",          # 分数：85分
            r"本批评分[:：]" + _num + r"分?",      # 本批评分：85分
            r"综合得分[:：]" + _num + r"分?",      # 综合得分：85分
            r"分值[:：]" + _num + r"分?",          # 分值：85分
            r"总分 \(Total Score\)[:：]" + _num + r"分?",  # 总分 (Total Score): 85
            r"Score[:：]" + _num,                   # Score: 85
            r"Total\s*Score[:：]" + _num,           # Total Score: 85
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, review_text)
            if match:
                try:
                    score = int(match.group(1))
                    # 确保评分在合理范围内
                    if 0 <= score <= 100:
                        return score
                except (ValueError, IndexError):
                    continue
        
        return 0


class BatchCodeReviewer(BaseReviewer):
    """支持分批审查 + LLM 合并报告的代码审查器"""

    def __init__(self):
        super().__init__("code_review_batch_prompt")
        self.merge_prompts = self._load_prompts("code_review_merge_prompt", get_env_with_default("REVIEW_STYLE"))

    def review_in_batches(self, files_json: List[Dict], commits_text: str = "") -> str:
        """
        审查一批文件变更。

        现代模型上下文窗口普遍 1M，全部 diff 未超预算时单批全量审查（模型一次看到完整
        上下文）。累计超预算时自动拆分为多批逐批审查，再用 LLM 合并为统一报告——
        确保所有文件都被审查到。单个超大文件 diff 会被截断，截断文件在结果末尾警告。

        Args:
            files_json: 文件变更列表
            commits_text: 提交信息

        Returns:
            审查报告
        """
        review_max_tokens = get_review_input_budget()

        if not files_json:
            return "无需要审查的文件"

        batches, truncated_files = self._pack_batches(files_json, review_max_tokens)
        logger.info(f'待审查文件数: {len(files_json)}, 预算 {review_max_tokens} tokens, '
                    f'打包为 {len(batches)} 批')

        # 单批：直接审查
        if len(batches) == 1:
            for file_entry in batches[0]:
                file_entry.pop('_truncated', None)
            diff_text = json.dumps(batches[0], ensure_ascii=False, indent=2)
            result = self.review_code(diff_text, commits_text).strip()
            if is_api_error_message(result):
                return result
            result = self._strip_markdown(result)
            if truncated_files:
                return result + self._build_truncation_warning(truncated_files, review_max_tokens)
            return result

        # 多批：逐批审查后合并
        logger.info(f'代码变更累计超预算，自动分 {len(batches)} 批逐批审查')
        batch_results = []
        batch_scores = []
        failed_batches = 0

        for i, batch in enumerate(batches):
            logger.info(f'分批审查: 第 {i + 1}/{len(batches)} 批, {len(batch)} 个文件')
            for file_entry in batch:
                file_entry.pop('_truncated', None)
            diff_text = json.dumps(batch, ensure_ascii=False, indent=2)
            result = self.review_code(diff_text, commits_text).strip()

            if is_api_error_message(result):
                logger.warning(f'分批 {i + 1} 审查失败: {result[:100]}')
                failed_batches += 1
                batch_results.append(f"## 第 {i + 1} 批 (审查失败)\n{result}")
                continue

            score = CodeReviewer.parse_review_score(result)
            batch_scores.append((score, len(batch)))
            batch_results.append(
                f"## 第 {i + 1} 批 (评分: {score}分, {len(batch)} 个文件)\n{self._strip_markdown(result)}")

        # 所有批都失败时直接降级拼接，避免浪费 LLM 合并调用
        if failed_batches == len(batches):
            logger.warning('所有批审查均失败，降级为拼接模式')
            summary_parts = '\n\n'.join(batch_results)
            return f"# 合并审查报告\n\n{summary_parts}\n\n**注意**: 各批审查均失败，以上为原始结果拼接。"

        merged = self._merge_reviews(batch_results, batch_scores, commits_text, failed_batches)
        if truncated_files:
            return merged + self._build_truncation_warning(truncated_files, review_max_tokens)
        return merged

    @staticmethod
    def _build_truncation_warning(truncated_files: List[str], budget: int) -> str:
        """构造截断警告文本（用户可见，附在审查报告末尾）"""
        logger.warning(f'共 {len(truncated_files)} 个文件 diff 超过输入预算被截断: '
                       f'{", ".join(truncated_files)}')
        return (
            f"\n\n---\n\n⚠️ **注意**: {len(truncated_files)} 个文件的 diff 超过单批输入预算"
            f"（{budget:,} tokens）已被截断，以下文件的审查结果可能不完整：\n"
            f"{'、'.join(truncated_files)}\n\n"
            f"建议在「🎯 审查设置」中调大「单次审查最大 Token 数」，"
            f"或拆分提交后分批审查。"
        )

    def _pack_batches(self, files_json: List[Dict], max_tokens: int,
                      max_files: int = 0) -> Tuple[List[List[Dict]], List[str]]:
        """
        将文件列表打包为审查批次，并收集被截断的文件。

        现代模型上下文窗口普遍 1M，全部 diff 未超预算时单批全量审查（模型一次看到完整
        上下文，避免跨文件问题被割裂）。当累计超过输入预算时自动拆分为多批，每批 diff
        ≤ 预算，逐批审查后合并报告——确保每个文件都被审查到：
        - 单个文件 diff 超过预算：截断该文件（分配整个预算）；
        - 多文件累计超过预算：按 token 贪心拆批，后续文件进入下一批。

        Args:
            files_json: 文件变更列表
            max_tokens: 每批 diff 的输入预算（token 上限）
            max_files: 保留参数以兼容历史调用，不再参与分批

        Returns:
            (batches, truncated_files): batches 为 1~N 批；truncated_files 为被截断的
            文件路径列表（单文件超限被截断），空表示无文件被截断。
        """
        if not files_json:
            return [], []

        truncated_files = []
        batches = []
        current_batch = []
        current_tokens = 0

        for file in files_json:
            diff = file.get('diff', '')
            file_tokens = count_tokens(diff)
            file_path = file.get('file_path', 'unknown')

            if file_tokens > max_tokens:
                # 单文件超限：单独一批并截断（分配整个预算）
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0
                # 预算留出 100 token 余量；max_tokens 很小（≤100）时至少截到 1 token，
                # 避免负数切片（tokens[:-100]）导致截断静默失效
                truncate_limit = max(1, max_tokens - 100)
                truncated_diff = truncate_text_by_tokens(diff, truncate_limit)
                file_copy = dict(file)
                file_copy['diff'] = truncated_diff
                file_copy['_truncated'] = True
                batches.append([file_copy])
                truncated_files.append(file_path)
                logger.warning(f'文件 {file_path} 超限: {file_tokens} tokens, '
                               f'截断至 {truncate_limit} tokens')
                continue

            if current_batch and current_tokens + file_tokens > max_tokens:
                # 累计超限：当前文件进入下一批
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(file)
            current_tokens += file_tokens

        if current_batch:
            batches.append(current_batch)

        return batches, truncated_files

    def _merge_reviews(self, batch_results: List[str], batch_scores: List[Tuple[int, int]],
                       commits_text: str, failed_count: int) -> str:
        """调用 LLM 合并多批审查结果为统一报告"""
        total_weight = sum(w for _, w in batch_scores)
        avg_score = sum(s * w for s, w in batch_scores) / total_weight if total_weight > 0 else 0

        summary_text = f"该提交共分 {len(batch_results)} 批审查，各批加权平均分: {avg_score:.1f} 分\n\n"
        for i, result in enumerate(batch_results):
            summary_text += f"--- 第 {i + 1} 批审查结果 ---\n{result}\n\n"

        if failed_count > 0:
            summary_text += f"\n⚠️ 注意: 有 {failed_count} 批审查失败，以上合并报告可能不完整。\n"

        messages = [
            self.merge_prompts["system_message"],
            {
                "role": "user",
                "content": self.merge_prompts["user_message"]["content"].format(
                    batch_results=summary_text,
                    commits_text=commits_text
                ),
            },
        ]

        result = self.call_llm(messages)
        if is_api_error_message(result):
            logger.warning("合并审查失败，降级为拼接模式")
            return f"# 合并审查报告\n\n{summary_text}\n**注意**: AI 合并失败，以上为各批原始结果的拼接。"

        result = result.strip()
        if result.startswith("```markdown") and result.endswith("```"):
            result = result[11:-3].strip()

        # 附加各批原始详述：合并阶段的 LLM 输出长度有限，文件较多时无法逐个复述，
        # 直接保留各批原文可确保每个被审查文件的详细意见都不会丢失。
        details = '\n\n'.join(batch_results)
        return f"{result}\n\n---\n\n# 各批原始审查详情（共 {len(batch_results)} 批）\n\n{details}"

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """审查一批代码"""
        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """去除 markdown 代码块标记"""
        if text.startswith("```markdown") and text.endswith("```"):
            return text[11:-3].strip()
        return text

