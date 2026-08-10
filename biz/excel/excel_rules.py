"""Excel 配置表规则检查模块

程序化规则预检，与 AI 语义审查解耦：
- 格式合规（format）：文件损坏、空表、表头问题、主键问题、空行、列数不齐
- 异常数值（numeric）：空值、非负列负数、百分比越界、数值列混入文本、异常量级

规则为内置启发式（基于列名与数据分布推断），更细的语义规则（枚举、跨表引用、
逻辑矛盾）由 AI 审查补充。规则检查结果会原样提供给 AI，作为语义审查的输入之一。
"""
from dataclasses import dataclass
from typing import Any, List, Optional

from biz.excel.excel_reader import SheetData, WorkbookData
from biz.utils.log import logger

# 列名启发式关键词（小写匹配英文；中文直接匹配）
# 疑似非负列：出现负数视为异常
NON_NEGATIVE_HINTS = (
    'price', 'cost', 'amount', 'count', 'num', 'quantity', 'hp', 'mp', 'attack',
    'defense', 'damage', 'speed', 'cd', 'cool', '剩余', '数量', '价格', '攻击',
    '防御', '伤害', '血量', '次数', '等级', 'level', '冷却', '概率', 'rate',
    'percent', 'probability', '比例', '占比',
)
# 疑似百分比列：值应在 0~100 之间
PERCENT_HINTS = ('rate', 'percent', 'prob', '概率', '比例', '占比', '%', '％')
# ID / 编码列：跳过"数值列混入文本"判断（ID 常为字符串）
ID_HINTS = ('id', 'key', 'code', '编号', '标识', '索引', 'name', '名称')

LARGE_NUMBER_THRESHOLD = 1_000_000_000
MIXED_TYPE_MIN_SAMPLES = 5
MIXED_TYPE_NUMERIC_RATIO = 0.9


@dataclass
class RuleIssue:
    """单条规则检查结果"""
    level: str               # error | warning
    category: str            # format | numeric
    sheet: str
    row: Optional[int]       # 1-based 文件行号（第1行=表头，第2行=第一条数据）
    col: Optional[str]
    message: str


def run_rule_checks(wb: WorkbookData) -> List[RuleIssue]:
    """对工作簿执行全部规则检查，返回问题列表（不抛异常）"""
    issues: List[RuleIssue] = []
    if wb.error:
        issues.append(RuleIssue('error', 'format', '-', None, None, f"文件解析失败: {wb.error}"))
        return issues
    for sheet in wb.sheets:
        _check_sheet(sheet, issues)
    return issues


def format_rule_issues(issues: List[RuleIssue]) -> str:
    """把规则检查结果格式化为文本，供 AI 审查使用"""
    if not issues:
        return "✅ 规则检查通过：未发现格式合规或异常数值问题"
    error_count = sum(1 for i in issues if i.level == 'error')
    warning_count = len(issues) - error_count
    lines = [f"⚠️ 规则检查发现 {len(issues)} 个问题（错误 {error_count} 个 / 警告 {warning_count} 个）："]
    for i in issues:
        loc = []
        if i.sheet:
            loc.append(f"Sheet={i.sheet}")
        if i.row:
            loc.append(f"行={i.row}")
        if i.col:
            loc.append(f"列={i.col}")
        loc_str = f" [{', '.join(loc)}]" if loc else ""
        level_tag = "❌" if i.level == 'error' else "⚠️"
        lines.append(f"- {level_tag} [{i.category}] {i.message}{loc_str}")
    return "\n".join(lines)


def _check_sheet(sheet: SheetData, issues: List[RuleIssue]) -> None:
    if not sheet.columns or not any(sheet.columns):
        issues.append(RuleIssue('error', 'format', sheet.name, None, None, "Sheet 没有有效的表头行"))
        return
    _check_header(sheet, issues)
    _check_rows(sheet, issues)


def _check_header(sheet: SheetData, issues: List[RuleIssue]) -> None:
    seen: dict = {}
    for col in sheet.columns:
        col_stripped = str(col).strip()
        if not col_stripped:
            issues.append(RuleIssue('error', 'format', sheet.name, 1, None, "表头存在空列名（缺少列名）"))
            continue
        seen[col_stripped] = seen.get(col_stripped, 0) + 1
        if any(ch.isspace() for ch in col_stripped):
            issues.append(RuleIssue(
                'warning', 'format', sheet.name, 1, col_stripped,
                f"表头 '{col_stripped}' 包含空白字符，建议去掉",
            ))
    for col, cnt in seen.items():
        if cnt > 1:
            issues.append(RuleIssue(
                'error', 'format', sheet.name, 1, col,
                f"表头 '{col}' 重复出现 {cnt} 次",
            ))


def _check_rows(sheet: SheetData, issues: List[RuleIssue]) -> None:
    if not sheet.rows:
        issues.append(RuleIssue('warning', 'format', sheet.name, None, None, "Sheet 没有数据行（空表）"))
        return
    col_count = len(sheet.columns)
    seen_keys: dict = {}
    numeric_counts = [0] * col_count
    non_empty_counts = [0] * col_count

    for row_idx, row in enumerate(sheet.rows):
        file_row = row_idx + 2  # 第1行表头，数据从第2行开始
        if all(v is None for v in row):
            issues.append(RuleIssue('warning', 'format', sheet.name, file_row, None, "整行为空（空行）"))
            continue
        if len(row) > col_count:
            issues.append(RuleIssue(
                'warning', 'format', sheet.name, file_row, None,
                f"该行有 {len(row)} 个单元格，超过表头列数 {col_count}",
            ))
        # 主键（首列）检查
        key = _cell_str(row[0]) if row else ''
        if not key.strip():
            issues.append(RuleIssue(
                'error', 'format', sheet.name, file_row, str(sheet.columns[0]) or None,
                "主键列（第一列）为空",
            ))
        else:
            seen_keys[key.strip()] = seen_keys.get(key.strip(), 0) + 1
        # 逐列数值检查
        for col_idx in range(col_count):
            v = row[col_idx] if col_idx < len(row) else None
            if v is None:
                if col_idx != 0:  # 主键空值已在上面报 error
                    issues.append(RuleIssue(
                        'warning', 'numeric', sheet.name, file_row, str(sheet.columns[col_idx]),
                        "存在空值",
                    ))
                continue
            non_empty_counts[col_idx] += 1
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                numeric_counts[col_idx] += 1
                _check_numeric_value(v, col_idx, sheet, file_row, issues)

    # 主键重复
    for key, cnt in seen_keys.items():
        if cnt > 1:
            issues.append(RuleIssue(
                'error', 'format', sheet.name, None, str(sheet.columns[0]),
                f"主键 '{key}' 重复出现 {cnt} 次",
            ))

    # 数值列混入文本
    _check_mixed_types(sheet, issues, numeric_counts, non_empty_counts)


def _check_numeric_value(v: Any, col_idx: int, sheet: SheetData, file_row: int, issues: List[RuleIssue]) -> None:
    col_name = str(sheet.columns[col_idx]).strip().lower()
    col_display = str(sheet.columns[col_idx]).strip() or None
    num = float(v)
    if any(h in col_name for h in PERCENT_HINTS) and (num > 100 or num < 0):
        issues.append(RuleIssue(
            'error', 'numeric', sheet.name, file_row, col_display,
            f"疑似百分比列出现越界值 {v}（应在 0~100 之间）",
        ))
    if any(h in col_name for h in NON_NEGATIVE_HINTS) and num < 0:
        issues.append(RuleIssue(
            'error', 'numeric', sheet.name, file_row, col_display,
            f"疑似非负列出现负数 {v}",
        ))
    if abs(num) > LARGE_NUMBER_THRESHOLD:
        issues.append(RuleIssue(
            'warning', 'numeric', sheet.name, file_row, col_display,
            f"数值 {v} 量级异常（|值| 超过 {LARGE_NUMBER_THRESHOLD}）",
        ))


def _check_mixed_types(sheet: SheetData, issues: List[RuleIssue], numeric_counts: List[int],
                       non_empty_counts: List[int]) -> None:
    for col_idx, col in enumerate(sheet.columns):
        col_display = str(col).strip() or None
        col_name = col_display.lower() if col_display else ''
        if any(h in col_name for h in ID_HINTS):
            continue  # ID/名称列常为字符串，跳过
        total = non_empty_counts[col_idx]
        if total < MIXED_TYPE_MIN_SAMPLES:
            continue  # 样本太少不做判断
        numeric_ratio = numeric_counts[col_idx] / total
        if MIXED_TYPE_NUMERIC_RATIO <= numeric_ratio < 1.0:
            issues.append(RuleIssue(
                'warning', 'numeric', sheet.name, None, col_display,
                "该列绝大多数是数值，但混入了少量文本（可能是录入错误）",
            ))


def _cell_str(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)
