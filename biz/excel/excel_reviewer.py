"""Excel 配置表 AI 语义审查器

在规则预检（格式合规 + 异常数值）之上，用 LLM 对配置表做语义层检查：
- 枚举值合法性（字段取值是否在合法集合内）
- 跨表引用一致性（引用的 ID 是否存在于关联配置表）
- 逻辑矛盾（数值关系、依赖关系、范围约束）
- 命名规范、字段含义合理性

架构：
- ExcelReviewer：单文件 = 规则预检结果 + 变更摘要 + 文本化表内容 → LLM 一次调用。
- ExcelAgenticReviewer：Agentic 模式，额外注册 read_excel_file 工具，
  AI 可跨表读取同仓库其他配置表做引用验证（仅 Agentic 启用时注册该工具）。

评分约定（与代码审查统一，保证总分正则只命中一处）：
- 单文件报告内 AI 输出"文件评估: XX分"；
- review_excel_files 合并多文件后，末尾统一输出一行"总分: XX分"（取各文件评估分最低值，
  代表整体风险），供 CodeReviewer.parse_review_score 提取。
"""
import re
from typing import Any, Callable, Dict, List, Optional

from biz.utils.code_reviewer import BaseReviewer, is_api_error_message
from biz.utils.default_config import get_env_int
from biz.utils.log import logger

from biz.excel.excel_reader import WorkbookData, workbook_to_text, workbook_statistics
from biz.excel.excel_rules import run_rule_checks, format_rule_issues

# 跨表引用工具 schema（Agentic 模式注册；工具名与 tool_context 的 key 对应）
EXCEL_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_excel_file",
            "description": (
                "读取同仓库中另一个 Excel 配置表（.xlsx/.xls/.csv）的指定 Sheet 内容，"
                "用于跨表引用验证（例如确认当前表引用的物品/技能/任务 ID 是否存在于对应的配置表）。"
                "只能读取本次审查所属仓库内的表格文件。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "表格文件路径，相对于 SVN 工作副本根目录（如 config/item.xlsx；"
                                       "也兼容带仓库根前缀的写法，如 trunk/config/item.xlsx）",
                    },
                    "sheet": {
                        "type": "string",
                        "description": "要读取的 Sheet 名（可选，默认第一个 Sheet）",
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "最多返回的行数，默认 100，最多 500",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
]

_TEXT_PROTOCOL_INSTRUCTIONS = """

### 工具调用格式（纯文本协议，当前模型不支持原生 function calling，请严格遵守）
如果需要调用工具获取更多信息，请只输出一行严格的 JSON，不要包含任何其他文字、解释或 markdown 代码块，格式如下：
{"tool_call": {"name": "工具名", "arguments": {"参数名": "参数值"}}}

可用工具与参数：
- read_excel_file：{"file_path": "相对于仓库根目录的表格文件路径", "sheet": "Sheet名(可选)", "max_rows": 100}

我会把工具执行结果发给你，你可以继续调用工具（最多若干轮），或者在获得足够信息后直接输出最终审查报告
（此时不能输出 tool_call JSON，必须是完整的 Markdown 审查报告）。
"""


def parse_file_score(review_text: str) -> Optional[int]:
    """解析单文件报告中的"文件评估: XX分"；解析不到返回 None（该文件不参与总分计算）"""
    if not review_text:
        return None
    # 兼容 AI 常见的 markdown 加粗/反引号包裹（如 "文件评估: **82分**"、"`文件评估: 82分`"），
    # 否则解析不到会按 0 分保守计入，导致总分虚低（曾出现 82 分被误计为 0 分）。
    match = re.search(r"文件评估[:：]\s*[*`]{0,2}\s*(\d+)\s*[*`]{0,2}\s*分?", review_text)
    if match:
        try:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
        except (ValueError, IndexError):
            pass
    return None


def _is_excel_ai_error(result: str) -> bool:
    """判断 AI 对 Excel 配置表的回复是否为错误/失败，而非正常审查报告。

    不能直接复用 is_api_error_message：它对短于 50 字符且无"审查关键词"的文本判为错误，
    而 Excel 的正常报告可能很短（例如只输出 "**文件评估: 85分**"），会被误判导致整个
    文件按 0 分处理。因此先看是否解析出"文件评估: XX分"——能解析出分数即视为正常报告。
    """
    if not result or not result.strip():
        return True
    if parse_file_score(result) is not None:
        return False  # 已给出文件评估分 → 正常报告
    return is_api_error_message(result)


class ExcelReviewer(BaseReviewer):
    """Excel 配置表审查器：规则预检结果 + 文本化表内容 → LLM 语义审查"""

    def __init__(self):
        super().__init__("excel_review_prompt")

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """满足 BaseReviewer 抽象接口；Excel 审查入口为 review_excel_file / review_excel_files"""
        return self._call_ai(diffs_text)

    def review_excel_file(self, file_path: str, wb_new: WorkbookData,
                          wb_old: Optional[WorkbookData] = None,
                          change_summary: Optional[str] = None,
                          commits_text: str = "",
                          max_rows: Optional[int] = None,
                          max_sheets: Optional[int] = None) -> str:
        """审查单个 Excel 文件，返回以 `### 📄 文件路径` 开头的报告（含"文件评估: XX分"）"""
        rule_issues = run_rule_checks(wb_new)
        if wb_new.error:
            return (f"### 📄 {file_path}\n\n"
                    f"**⚠️ 文件解析失败，无法进行语义检查**\n\n"
                    f"{wb_new.error}\n\n"
                    f"**文件评估: 0分**")
        user_content = self._build_user_content(
            file_path, wb_new, rule_issues, change_summary, commits_text, max_rows, max_sheets,
        )
        result = self._call_ai(user_content)
        if _is_excel_ai_error(result):
            logger.warning(f'Excel 配置表语义审查遇到错误: {result[:100]}...')
            return (f"### 📄 {file_path}\n\n"
                    f"**⚠️ AI 语义审查失败**（{result[:200]}），仅保留规则预检结果：\n\n"
                    f"{format_rule_issues(rule_issues)}\n\n"
                    f"**文件评估: 0分**")
        return f"### 📄 {file_path}\n\n{result}"

    def _build_user_content(self, file_path: str, wb_new: WorkbookData, rule_issues: List,
                            change_summary: Optional[str], commits_text: str,
                            max_rows: Optional[int], max_sheets: Optional[int]) -> str:
        max_rows = max_rows or get_env_int("EXCEL_REVIEW_MAX_ROWS", 500)
        max_sheets = max_sheets or get_env_int("EXCEL_REVIEW_MAX_SHEETS", 20)
        table_text = workbook_to_text(wb_new, max_rows=max_rows, max_sheets=max_sheets)
        # 全表列统计：正文按 max_rows 截断，大表后半部分行 AI 看不到，
        # 但列统计（非空/唯一值/类型/min-max/枚举示例）基于全表，补充全貌。
        table_stats = workbook_statistics(wb_new, max_sheets=max_sheets)
        return self.prompts["user_message"]["content"].format(
            table_content=table_text,
            table_statistics=table_stats,
            rule_issues=format_rule_issues(rule_issues),
            change_summary=change_summary or "无（新增文件，无历史版本可对比）",
            commits_text=commits_text or "无",
        )

    def _call_ai(self, user_content: str) -> str:
        """单次 LLM 调用（Agentic 子类覆盖为工具调用循环）"""
        messages = [
            self.prompts["system_message"],
            {"role": "user", "content": user_content},
        ]
        return (self.call_llm(messages) or "").strip()


class ExcelAgenticReviewer(ExcelReviewer):
    """Agentic 模式的 Excel 审查器：提供 read_excel_file 工具支持跨表引用检查"""

    def __init__(self, tool_context: Optional[Dict[str, Callable]] = None):
        super().__init__()
        self.tool_context = tool_context or {}
        self.max_tool_rounds = get_env_int("AGENTIC_REVIEW_MAX_TOOL_ROUNDS", 5)

    def _call_ai(self, user_content: str) -> str:
        """工具调用循环；最终仍失败（返回错误）时降级为不带工具调用的普通审查，
        保证该文件至少能拿到一次正常审查结果，而不是让整次审查彻底失败（对齐
        AgenticCodeReviewer 的降级安全网，已知 Jedi 网关存在"思考截断"问题）。"""
        if not self.tool_context:
            return super()._call_ai(user_content)
        if getattr(self.client, "supports_tools", False):
            result = self._run_native_tools_loop(user_content)
        else:
            result = self._run_text_protocol_loop(user_content)
        if _is_excel_ai_error(result):
            logger.warning("Excel 配置表工具调用审查最终失败，降级为不带工具调用的普通审查")
            return super()._call_ai(user_content)
        return result

    def _run_native_tools_loop(self, user_content: str) -> str:
        """原生 function calling 路径"""
        messages: List[Dict[str, Any]] = [
            self.prompts["system_message"],
            {"role": "user", "content": user_content},
        ]
        for round_idx in range(self.max_tool_rounds):
            response = self.client.completions_with_tools(messages, EXCEL_TOOLS_SCHEMA)
            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                return response.get("content") or ""
            messages.append(response["assistant_message"])
            logger.info(
                f"Excel 配置表审查请求调用工具 (原生协议, 第{round_idx + 1}轮): "
                f"{[c['name'] for c in tool_calls]}"
            )
            for call in tool_calls:
                result_text = self._dispatch_tool(call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result_text,
                })
        logger.warning(f"Excel 配置表审查已达到最大工具调用轮数({self.max_tool_rounds})，强制要求给出最终结论")
        messages.append({
            "role": "user",
            "content": "已达到本次审查的最大工具调用次数，请直接基于当前已获得的信息给出最终审查报告，不要再调用工具。",
        })
        response = self.client.completions_with_tools(messages, [])
        return response.get("content") or ""

    def _run_text_protocol_loop(self, user_content: str) -> str:
        """纯文本协议模拟路径（ollama/jedi 等不支持原生 function calling 的客户端）"""
        from biz.utils.agentic_reviewer import AgenticCodeReviewer  # 复用纯文本解析器

        system_message = dict(self.prompts["system_message"])
        system_message["content"] = system_message["content"] + _TEXT_PROTOCOL_INSTRUCTIONS
        messages: List[Dict[str, Any]] = [
            system_message,
            {"role": "user", "content": user_content},
        ]
        for round_idx in range(self.max_tool_rounds):
            content = self.client.completions(messages) or ""
            tool_call = AgenticCodeReviewer._parse_text_tool_call(content)
            if tool_call is None:
                return content
            logger.info(
                f"Excel 配置表审查请求调用工具 (文本协议, 第{round_idx + 1}轮): {tool_call['name']}"
            )
            messages.append({"role": "assistant", "content": content})
            result_text = self._dispatch_tool(tool_call)
            messages.append({
                "role": "user",
                "content": f"工具 {tool_call['name']} 返回结果：\n{result_text}\n\n"
                           f"请继续审查；如已获得足够信息，请直接输出最终审查报告（不要再输出 tool_call）。",
            })
        logger.warning(f"Excel 配置表审查(文本协议)已达到最大工具调用轮数({self.max_tool_rounds})，强制要求给出最终结论")
        messages.append({
            "role": "user",
            "content": "已达到本次审查的最大工具调用次数，请直接给出最终审查报告，不要再输出 tool_call。",
        })
        return self.client.completions(messages) or ""

    def _dispatch_tool(self, call: Dict[str, Any]) -> str:
        """执行单个工具调用；任何异常/未知工具都返回可读错误文本，不中断审查"""
        name = call.get("name")
        arguments = call.get("arguments") or {}
        handler = self.tool_context.get(name)
        if handler is None:
            return f"错误: 未知或不可用的工具 '{name}'"
        try:
            if name == "read_excel_file":
                return handler(
                    arguments.get("file_path", ""),
                    arguments.get("sheet"),
                    arguments.get("max_rows", 100),
                ) or "文件内容为空"
            return f"错误: 未实现的工具 '{name}'"
        except Exception as e:
            logger.warning(f"工具调用执行失败 ({name}): {e}")
            return f"错误: 工具执行失败 - {e}"


def review_excel_files(excel_files: List[Dict], commits_text: str = "",
                       agentic: bool = False,
                       tool_context: Optional[Dict[str, Callable]] = None,
                       max_rows: Optional[int] = None,
                       max_sheets: Optional[int] = None) -> tuple:
    """审查多个 Excel 文件并合并报告

    :param excel_files: [{file_path, status, wb_new, wb_old, change_summary}]
    :param commits_text: 提交信息文本
    :param agentic: 是否使用 Agentic 审查（启用 read_excel_file 跨表引用工具）
    :param tool_context: read_excel_file 工具的执行上下文（handler 可调用对象）
    :return: (report, score)；report 每文件一节，末尾统一"总分: XX分"（取各文件评估分最低值）
    """
    if not excel_files:
        return "无需要审查的配置表", 0
    reviewer = ExcelAgenticReviewer(tool_context=tool_context) if agentic else ExcelReviewer()
    reports: List[str] = []
    file_scores: List[int] = []
    for f in excel_files:
        file_path = f.get('file_path', '未知文件')
        try:
            report = reviewer.review_excel_file(
                file_path=file_path,
                wb_new=f.get('wb_new'),
                wb_old=f.get('wb_old'),
                change_summary=f.get('change_summary'),
                commits_text=commits_text,
                max_rows=max_rows,
                max_sheets=max_sheets,
            )
        except Exception as e:
            logger.error(f'Excel 配置表审查异常 ({file_path}): {type(e).__name__}: {e}')
            report = (f"### 📄 {file_path}\n\n"
                      f"**❌ AI 审查失败**：{type(e).__name__}: {str(e)[:200]}\n\n"
                      f"**文件评估: 0分**")
        # 清理 AI 单文件报告内自带的"总分: XX分"：外层会统一追加唯一的"总分"，
        # 若 AI 不遵守输出格式也输出了"总分"，会导致 CodeReviewer.parse_review_score
        # 用 re.search 从头匹配到 AI 的分数而不是合并后的总分（H2）。
        # 同样兼容 markdown 加粗/反引号包裹（如 "总分: **85分**"）。
        report = re.sub(r'总分\s*[:：]?\s*[*`]{0,2}\s*\d+\s*[*`]{0,2}\s*分?', '', report)
        # 文件评估分解析不到（AI 报告跑偏）按 0 分处理，保守起见计入最低分，
        # 并在报告里明示，避免"0 分来源不明"难以排查。
        score = parse_file_score(report)
        if score is None:
            report = f"{report}\n\n**⚠️ AI 未按输出格式给出「文件评估: XX分」，已按 0 分保守计入**"
        file_scores.append(score if score is not None else 0)
        reports.append(report)
    report_text = "\n\n---\n\n".join(reports)
    total_score = min(file_scores) if file_scores else 0
    report_text += f"\n\n**总分: {total_score}分**"
    return report_text, total_score
