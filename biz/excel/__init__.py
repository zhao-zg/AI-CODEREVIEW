"""
Excel 配置表审查模块
========================
为 SVN 链路新增的 Excel 配置表（策划配置表）审查能力。

三层检查：
1. 格式合规检查（excel_rules）：文件损坏、空表、表头/主键问题、空行、列数不齐
2. 异常数值检查（excel_rules）：空值、非负列负数、百分比越界、数值列混入文本、异常量级
3. AI 语义检查（excel_reviewer）：枚举值合法性、跨表引用一致性、逻辑矛盾、命名规范

读取二进制 .xlsx 依赖 SVNHandler.svn_cat_bytes（原始字节），解析用 pandas + openpyxl / xlrd。

注意：本模块使用**惰性 re-export**（PEP 562 __getattr__）。导入 biz.excel 不会连带导入
excel_reviewer → code_reviewer → LLM factory 链（openai / zhipuai / ollama 等），
只有实际访问子模块符号时才触发对应子模块导入。避免"仅想用 excel_reader 却要求
LLM 客户端依赖全部安装"的连带导入问题（此前 svn_worker 捕获 ImportError 后
会把缺 openai 误报成"缺 openpyxl / xlrd"）。
"""
from typing import Any, List

# 符号名 → 所属子模块（惰性导入映射）
_LAZY_EXPORTS: dict = {
    "WorkbookData": "biz.excel.excel_reader",
    "SheetData": "biz.excel.excel_reader",
    "parse_workbook": "biz.excel.excel_reader",
    "workbook_to_text": "biz.excel.excel_reader",
    "workbook_statistics": "biz.excel.excel_reader",
    "compare_workbooks": "biz.excel.excel_reader",
    "format_change_summary": "biz.excel.excel_reader",
    "RuleIssue": "biz.excel.excel_rules",
    "run_rule_checks": "biz.excel.excel_rules",
    "format_rule_issues": "biz.excel.excel_rules",
    "ExcelReviewer": "biz.excel.excel_reviewer",
    "ExcelAgenticReviewer": "biz.excel.excel_reviewer",
    "review_excel_files": "biz.excel.excel_reviewer",
}

__all__: List[str] = sorted(_LAZY_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    """PEP 562：访问顶层符号时惰性导入对应子模块"""
    module = _LAZY_EXPORTS.get(name)
    if module is not None:
        import importlib
        return getattr(importlib.import_module(module), name)
    raise AttributeError(f"module 'biz.excel' has no attribute '{name}'")


def __dir__() -> List[str]:
    return sorted(set(globals().keys()) | set(_LAZY_EXPORTS.keys()))
