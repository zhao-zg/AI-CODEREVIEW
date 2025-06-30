# -*- coding: utf-8 -*-
"""数据显示模块 - 重构优化版本，模块化设计"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta
import logging

# 导入自定义模块
from .data_processor import DataProcessor
from .analytics import AnalyticsEngine
from .ui_components import UIComponents
from .export_utils import DataExporter

logger = logging.getLogger(__name__)


class DataDisplayManager:
    """数据显示管理器 - 统一管理所有数据显示功能"""
    
    def __init__(self):
        self.processor = DataProcessor()
        self.analytics = AnalyticsEngine()
        self.ui = UIComponents()
        self.exporter = DataExporter()
    
    def display_version_tracking_data(self, review_type: str = "mr", 
                                    authors: Optional[List[str]] = None, 
                                    projects: Optional[List[str]] = None, 
                                    date_range: Optional[Tuple] = None, 
                                    score_range: Tuple[int, int] = (0, 100)) -> None:
        """显示版本追踪数据 - 重构优化版本"""
        
        try:
            
            # 获取数据服务
            from biz.service.review_service import ReviewService
            review_service = ReviewService()
            
            # 显示查询摘要
            self.ui.show_query_summary(review_type, authors, projects, date_range, score_range)
            
            # 获取和预处理数据
            with self.ui.show_loading_spinner("正在获取数据..."):
                df = self._get_and_preprocess_data(review_service, review_type, authors, projects, date_range, score_range)
            
            if df is None or df.empty:
                self.ui.show_no_data_help(review_type)
                return
            
            # 创建主要功能标签页
            main_tabs = st.tabs(["📋 详细数据", "📊 统计分析", "📈 图表分析", "📥 数据导出"])
            with main_tabs[0]:
                self._show_enhanced_data_table(df, review_type)

            with main_tabs[1]:
                self.analytics.show_statistics_panel(df, review_type)
            
            with main_tabs[2]:
                self.analytics.show_charts_analysis(df, review_type)
            
            with main_tabs[3]:
                self.exporter.show_export_panel(df, review_type)
                
        except Exception as e:
            logger.error(f"显示{review_type}数据时发生错误: {str(e)}")
            self.ui.show_error_message(f"数据显示出现错误: {str(e)}")
            st.exception(e)
    
    def _get_and_preprocess_data(self, review_service, review_type, authors, projects, date_range, score_range):
        """获取和预处理数据"""
        try:
            # 解析日期范围
            start_date = end_date = None
            if date_range:
                start_date = date_range[0].strftime('%Y-%m-%d') if date_range[0] else None
                end_date = date_range[1].strftime('%Y-%m-%d') if date_range[1] else None
            
            # 获取数据
            result = review_service.get_review_statistics(
                review_type=review_type,
                start_date=start_date,
                end_date=end_date
            )
            
            # 处理响应
            if isinstance(result, dict):
                if not result.get('success', True):
                    self.ui.show_error_message(f"获取数据失败: {result.get('message', '未知错误')}")
                    return None
                data = result.get('data', result)
            else:
                data = result
            
            if not data:
                return pd.DataFrame()
            
            # 转换为DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                logger.warning(f"未知数据类型: {type(data)}")
                return pd.DataFrame()
            
            # 预处理数据
            df = self.processor.preprocess_dataframe(df)
            
            # 应用筛选
            df = self.processor.apply_filters(df, authors, projects, score_range)
            
            return df
            
        except Exception as e:
            logger.error(f"获取数据时发生错误: {str(e)}")
            self.ui.show_error_message(f"获取数据失败: {str(e)}")
            return None
    
    def _show_enhanced_data_table(self, df: pd.DataFrame, review_type: str):
        """显示增强的数据表"""
        st.markdown("### 📋 数据详情")
        
        # 创建控制面板
        controls = self.ui.create_data_table_controls()
        
        # 应用搜索筛选
        display_df = df.copy()
        if controls['search_term']:
            mask = self._apply_search_filter(display_df, controls['search_term'])
            display_df = display_df[mask]
        
        # 应用排序
        display_df = self._apply_sorting(display_df, controls['sort_by'])
        
        # 显示筛选结果
        total_rows = len(display_df)
        if total_rows == 0:
            self.ui.show_warning_message("没有找到匹配的数据记录")
            return
        
        # 分页处理
        page_size = controls['page_size']
        total_pages = (total_rows - 1) // page_size + 1 if total_rows > 0 else 1
        
        # 分页控制
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        with page_col2:
            current_page = st.number_input(
                f"页码 (共 {total_pages} 页，{total_rows} 条记录)",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1
            )
        
        # 当前页数据
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_rows)
        page_data = display_df.iloc[start_idx:end_idx]
        
        st.markdown("---")
        # 显示数据卡片
        self._display_data_cards(page_data, review_type, start_idx)
    
    def _apply_search_filter(self, df: pd.DataFrame, search_term: str) -> pd.Series:
        """应用搜索筛选"""
        text_columns = df.select_dtypes(include=['object']).columns
        mask = pd.Series(False, index=df.index)
        
        for col in text_columns:
            mask |= df[col].astype(str).str.contains(search_term, case=False, na=False)
        
        return mask
    
    def _apply_sorting(self, df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
        """应用排序"""
        if sort_by == "时间倒序" and 'datetime' in df.columns:
            return df.sort_values('datetime', ascending=False, na_position='last')
        elif sort_by == "时间正序" and 'datetime' in df.columns:
            return df.sort_values('datetime', ascending=True, na_position='last')
        elif sort_by == "评分倒序" and 'score' in df.columns:
            return df.sort_values('score', ascending=False, na_position='last')
        elif sort_by == "评分正序" and 'score' in df.columns:
            return df.sort_values('score', ascending=True, na_position='last')
        elif sort_by == "作者" and 'author' in df.columns:
            return df.sort_values('author', ascending=True, na_position='last')
        elif sort_by == "项目" and 'project_name' in df.columns:
            return df.sort_values('project_name', ascending=True, na_position='last')
        else:
            return df
    def _display_data_cards(self, page_data: pd.DataFrame, review_type: str, start_idx: int):
        """显示数据卡片"""
        for idx, (_, row) in enumerate(page_data.iterrows()):
            actual_index = start_idx + idx + 1
            
            # 显示数据卡片并获取状态
            card_state = self.ui.show_data_card(row, actual_index, review_type)
            
            # 只有当卡片处于展开状态时才显示详情
            if card_state == "expanded":
                with st.container():
                    st.markdown("---")
                    self.ui.show_detail_modal(row, review_type)
                    st.markdown("---")


# 创建全局数据显示管理器实例
display_manager = DataDisplayManager()

# 导出主要函数以保持向后兼容性
def display_version_tracking_data(*args, **kwargs):
    """向后兼容的函数"""
    return display_manager.display_version_tracking_data(*args, **kwargs)

def display_legacy_data():
    """显示遗留数据"""
    st.info("遗留数据显示功能")
