"""Excel 配置表读取与解析模块

支持 .xlsx / .xls / .csv 三种表格格式的解析，统一转换为 WorkbookData 结构，
供规则检查（格式合规 / 异常数值）与 AI 语义审查（文本化）使用。

设计原则：
- 解析失败不抛异常，返回带 error 信息的 WorkbookData，由上层决定如何处置；
- 单元格值保留原始 Python 类型（int/float/str/None/bool），供规则检查做类型判断；
- 文本化（workbook_to_text）时再统一转字符串，输出 markdown 表格。
"""
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from biz.utils.log import logger

SUPPORTED_EXTENSIONS = ('.xlsx', '.xlsm', '.xls', '.csv')

# 匹配纯数字字符串（含正负号/小数），如 10、-3、3.5；用于把 pandas 3.0 读 csv 得到的数字字符串转回数值
_NUMERIC_RE = re.compile(r'^[+-]?\d+(\.\d+)?$')


@dataclass
class SheetData:
    """单个 Sheet 的数据"""
    name: str
    columns: List[str]            # 表头（第一行），空单元格为 ''
    rows: List[List[Any]]         # 数据行（第二行起），空单元格为 None，已去除整行全空的行
    row_count: int                # 数据行数


@dataclass
class WorkbookData:
    """整个工作簿的解析结果"""
    file_name: str
    sheets: List[SheetData] = field(default_factory=list)
    error: Optional[str] = None   # 解析失败时的错误信息，非空表示整体解析失败


def _normalize_cell(value: Any) -> Any:
    """规范化单元格值：NaN/NaT → None；整数值 float 还原为 int；pandas/numpy 标量转 Python 标量；日期转字符串"""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    # pandas 3.0 nullable dtype（Int64/Float64/StringDtype）下的标量转回 Python 标量
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        f = float(value)
        return int(f) if f.is_integer() else f
    if isinstance(value, str):
        # pandas 3.0 起 read_csv 默认把数字也读成字符串，这里按需转回数值，
        # 以便规则检查做类型/数值判断；带前导零的 ID（如 "001"）保持字符串不转换。
        # 注意：'10.0' 要转成 int 10（与 xlsx 读取的整数类型保持一致），
        # 否则同一数据 csv↔xlsx 格式迁移时新旧对比会误报整列"修改"。
        s = value.strip()
        if s and _NUMERIC_RE.match(s):
            if s[0] == '0' and len(s) > 1 and not s.startswith(('+', '-')) and '.' not in s:
                return value
            try:
                if '.' in s:
                    f = float(s)
                    return int(f) if f.is_integer() else f
                return int(s)
            except ValueError:
                pass
        return value
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _cell_to_str(value: Any) -> str:
    """单元格值 → 显示字符串（None → ''，bool → true/false）"""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _escape_cell(text: str) -> str:
    """markdown 表格单元格转义：| → \\|，换行 → 空格"""
    return text.replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')


def _dataframe_to_sheet(sheet_name: str, df: pd.DataFrame) -> SheetData:
    """把 pandas 读出的 DataFrame（header=None 模式）转成 SheetData，第一行作为表头"""
    if df is None or df.empty:
        return SheetData(name=sheet_name, columns=[], rows=[], row_count=0)
    raw = df.values.tolist()
    header = [_cell_to_str(_normalize_cell(v)) for v in raw[0]]
    rows = [[_normalize_cell(v) for v in row] for row in raw[1:]]
    # 去除整行全空的行（合并单元格 / 末尾空白行在 pandas 中可能产生全 NaN 行）
    rows = [row for row in rows if any(v is not None for v in row)]
    return SheetData(name=sheet_name, columns=header, rows=rows, row_count=len(rows))


def parse_workbook(data: bytes, filename: str) -> WorkbookData:
    """解析表格文件字节，返回 WorkbookData；任何失败都以 error 字段返回，不抛异常

    :param data: 文件原始字节（来自 SVNHandler.svn_cat_bytes）
    :param filename: 文件名（用于判断扩展名）
    """
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext == '.csv':
            return _parse_csv(data, filename)
        if ext in ('.xlsx', '.xlsm'):
            return _parse_excel(data, filename, engine='openpyxl')
        if ext == '.xls':
            return _parse_excel(data, filename, engine='xlrd')
        return WorkbookData(file_name=filename, sheets=[], error=f"不支持的表格格式: {ext}")
    except Exception as e:
        logger.error(f'Excel 配置表解析异常 ({filename}): {type(e).__name__}: {e}')
        return WorkbookData(file_name=filename, sheets=[], error=f"解析失败: {type(e).__name__}: {str(e)[:200]}")


def _parse_excel(data: bytes, filename: str, engine: str) -> WorkbookData:
    """解析 .xlsx / .xls"""
    try:
        sheets_dict = pd.read_excel(BytesIO(data), sheet_name=None, engine=engine, header=None)
    except ImportError:
        return WorkbookData(
            file_name=filename, sheets=[],
            error=f"缺少 {engine} 依赖，请安装 openpyxl / xlrd 后重试",
        )
    except Exception as e:
        return WorkbookData(
            file_name=filename, sheets=[],
            error=f"{engine} 解析失败: {type(e).__name__}: {str(e)[:200]}",
        )
    sheets = [_dataframe_to_sheet(str(name), df) for name, df in sheets_dict.items()]
    return WorkbookData(file_name=filename, sheets=sheets)


def _parse_csv(data: bytes, filename: str) -> WorkbookData:
    """解析 .csv：按 utf-8-sig / gbk / utf-8 依次尝试编码

    注意：pandas 3.0 起 read_csv 默认把全表读成 StringDtype（数字列也是字符串），
    必须显式指定 dtype_backend='numpy_nullable' 才能恢复数值推断。
    """
    last_err: Optional[Exception] = None
    for encoding in ('utf-8-sig', 'gbk', 'utf-8'):
        try:
            df = pd.read_csv(BytesIO(data), header=None, encoding=encoding, dtype_backend='numpy_nullable')
            sheet = _dataframe_to_sheet(os.path.basename(filename), df)
            return WorkbookData(file_name=filename, sheets=[sheet])
        except UnicodeDecodeError as e:
            last_err = e
        except Exception as e:
            return WorkbookData(
                file_name=filename, sheets=[],
                error=f"CSV 解析失败: {type(e).__name__}: {str(e)[:200]}",
            )
    return WorkbookData(file_name=filename, sheets=[], error=f"CSV 编码无法识别: {last_err}")


def workbook_to_text(wb: WorkbookData, max_rows: int = 500, max_sheets: int = 20) -> str:
    """把工作簿文本化为 markdown 表格，供 AI 语义审查使用（超出部分截断）"""
    if wb.error:
        return f"[文件解析错误] {wb.error}"
    parts = [f"文件名: {wb.file_name}", f"Sheet 数量: {len(wb.sheets)}"]
    for idx, sheet in enumerate(wb.sheets[:max_sheets]):
        parts.append(f"\n### Sheet[{idx}]: {sheet.name}（{sheet.row_count} 行数据）")
        if not sheet.columns or not any(sheet.columns):
            parts.append("⚠️ 该 Sheet 没有有效的表头")
            continue
        lines = [
            "| " + " | ".join(_escape_cell(c) for c in sheet.columns) + " |",
            "|" + "---|" * len(sheet.columns),
        ]
        shown = 0
        for row in sheet.rows[:max_rows]:
            cells = []
            for i in range(len(sheet.columns)):
                v = row[i] if i < len(row) else None
                cells.append(_escape_cell(_cell_to_str(v)))
            lines.append("| " + " | ".join(cells) + " |")
            shown += 1
        if sheet.row_count > shown:
            lines.append(f"…（共 {sheet.row_count} 行，仅显示前 {shown} 行）")
        parts.append("\n".join(lines))
    if len(wb.sheets) > max_sheets:
        parts.append(f"\n…（共 {len(wb.sheets)} 个 Sheet，仅显示前 {max_sheets} 个）")
    return "\n".join(parts)


def workbook_statistics(wb: WorkbookData, max_unique: int = 15, max_sheets: int = 20) -> str:
    """生成工作簿的列统计信息（基于**全表**），供 AI 语义审查补充正文截断之外的全貌。

    大表（超出 EXCEL_REVIEW_MAX_ROWS 截断）的 AI 审查看不到后半部分行，
    但列统计可以给出：每列 非空数/唯一值数/类型/数值min-max/枚举示例，
    AI 据此仍能判断枚举值合法性、数值范围合理性、空值比例等全表级语义问题。

    :param wb: 工作簿
    :param max_unique: 每列最多展示的唯一值个数（文本列的"枚举示例"）
    :param max_sheets: 最多统计的 Sheet 数量
    """
    if wb.error:
        return f"[文件解析错误] {wb.error}"
    parts = []
    for idx, sheet in enumerate(wb.sheets[:max_sheets]):
        parts.append(f"\n### Sheet[{idx}]: {sheet.name} 列统计（全表 {sheet.row_count} 行）")
        if not sheet.columns or not any(sheet.columns):
            parts.append("无有效表头")
            continue
        lines = ["| 列名 | 非空数 | 唯一值数 | 类型 | 统计 |", "|---|---|---|---|---|"]
        for col_idx, col in enumerate(sheet.columns):
            col_name = str(col).strip()
            if not col_name:
                col_name = f"(第{col_idx + 1}列)"
            values = [
                row[col_idx] for row in sheet.rows
                if col_idx < len(row) and row[col_idx] is not None
            ]
            non_empty = len(values)
            unique: set = set()
            numeric_vals: List[float] = []
            for v in values:
                if isinstance(v, bool):
                    unique.add('true' if v else 'false')
                elif isinstance(v, (int, float)):
                    unique.add(str(v))
                    numeric_vals.append(float(v))
                else:
                    unique.add(str(v))
            if non_empty == 0:
                stat = "全列为空"
                col_type = "空"
            else:
                numeric_ratio = len(numeric_vals) / non_empty
                if numeric_ratio >= 0.9:
                    col_type = "数值"
                    stat = f"min={min(numeric_vals):g}, max={max(numeric_vals):g}"
                elif numeric_ratio > 0:
                    col_type = "混合"
                    stat = f"数值占比 {numeric_ratio:.0%}"
                else:
                    col_type = "文本"
                    uniq_list = [str(u)[:30] for u in sorted(unique, key=str)[:max_unique]]
                    stat = "枚举示例: " + ", ".join(uniq_list)
                    if len(unique) > max_unique:
                        stat += f" …（共 {len(unique)} 个唯一值）"
            lines.append("| " + " | ".join(_escape_cell(c) for c in
                                           [col_name, str(non_empty), str(len(unique)), col_type, stat]) + " |")
        parts.append("\n".join(lines))
    if len(wb.sheets) > max_sheets:
        parts.append(f"\n…（共 {len(wb.sheets)} 个 Sheet，仅统计前 {max_sheets} 个）")
    return "\n".join(parts)


@dataclass
class ChangeSummary:
    """新旧工作簿对比后的单条变更"""
    sheet_name: str
    action: str                                       # added_row / deleted_row / modified_row / added_sheet / deleted_sheet
    key: str
    fields: List[Tuple[str, str, str]] = field(default_factory=list)  # (column, old_value, new_value)


def compare_workbooks(old: WorkbookData, new: WorkbookData) -> List[ChangeSummary]:
    """按 sheet 名 + 首列主键对比新旧工作簿，输出变更摘要（用于修改文件的变更行重点审查）"""
    changes: List[ChangeSummary] = []
    old_sheets = {s.name: s for s in old.sheets}
    new_sheets = {s.name: s for s in new.sheets}

    for name, ns in new_sheets.items():
        os_ = old_sheets.get(name)
        if os_ is None:
            changes.append(ChangeSummary(sheet_name=name, action='added_sheet', key='', fields=[]))
            continue
        changes.extend(_compare_sheets(os_, ns))
    for name in old_sheets:
        if name not in new_sheets:
            changes.append(ChangeSummary(sheet_name=name, action='deleted_sheet', key='', fields=[]))
    return changes


def _compare_sheets(old_sheet: SheetData, new_sheet: SheetData) -> List[ChangeSummary]:
    """对比两个同名 Sheet，按首列主键找出 新增行 / 删除行 / 修改行"""
    changes: List[ChangeSummary] = []
    old_map, old_cols = _index_rows(old_sheet)
    new_map, _ = _index_rows(new_sheet)

    for key, new_row in new_map.items():
        old_row = old_map.get(key)
        if old_row is None:
            changes.append(ChangeSummary(sheet_name=new_sheet.name, action='added_row', key=str(key), fields=[]))
            continue
        diffs: List[Tuple[str, str, str]] = []
        for i, col in enumerate(new_sheet.columns):
            new_val = new_row[i] if i < len(new_row) else None
            j = old_cols.get(col)
            old_val = old_row[j] if j is not None and j < len(old_row) else None
            if _cell_to_str(old_val) != _cell_to_str(new_val):
                diffs.append((col, _cell_to_str(old_val), _cell_to_str(new_val)))
        if diffs:
            changes.append(ChangeSummary(
                sheet_name=new_sheet.name, action='modified_row', key=str(key), fields=diffs,
            ))
    for key in old_map:
        if key not in new_map:
            changes.append(ChangeSummary(sheet_name=new_sheet.name, action='deleted_row', key=str(key), fields=[]))
    return changes


def _index_rows(sheet: SheetData) -> Tuple[Dict[str, List[Any]], Dict[str, int]]:
    """按首列建索引：{首列值: 行}；返回 (行索引, 列名→下标)"""
    rows_map: Dict[str, List[Any]] = {}
    col_index = {col: i for i, col in enumerate(sheet.columns)}
    for row in sheet.rows:
        if not row or row[0] is None:
            continue
        key = _cell_to_str(row[0]).strip()
        if not key:
            continue
        rows_map.setdefault(key, row)
    return rows_map, col_index


def format_change_summary(changes: List[ChangeSummary], max_items: int = 200) -> str:
    """把变更摘要格式化为文本，供 AI 审查与规则检查报告使用"""
    if not changes:
        return "无变更（内容与上一版本一致）"
    action_labels = {
        'added_row': '新增行', 'deleted_row': '删除行', 'modified_row': '修改行',
        'added_sheet': '新增Sheet', 'deleted_sheet': '删除Sheet',
    }
    lines = [f"与上一版本相比，共 {len(changes)} 处变更（仅列出前 {max_items} 处）："]
    for c in changes[:max_items]:
        label = action_labels.get(c.action, c.action)
        if c.action == 'modified_row':
            field_desc = "；".join(f"{col}: {old} → {new}" for col, old, new in c.fields[:10])
            lines.append(f"- [{label}] 主键={c.key}：{field_desc}")
        elif c.action in ('added_row', 'deleted_row'):
            lines.append(f"- [{label}] 主键={c.key}")
        else:
            lines.append(f"- [{label}] {c.sheet_name}")
    if len(changes) > max_items:
        lines.append(f"…（还有 {len(changes) - max_items} 处变更未列出）")
    return "\n".join(lines)
