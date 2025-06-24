# -*- coding: utf-8 -*-
"""导出工具模块 - 负责数据导出功能"""

import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
import json
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataExporter:
    """数据导出器类"""
    
    def __init__(self):
        self.supported_formats = ['CSV', 'Excel', 'JSON']
    
    def export_data(self, df: pd.DataFrame, format_type: str, review_type: str, filename_prefix: str = None):
        """导出数据到指定格式"""
        if df.empty:
            st.warning("📥 没有数据可以导出")
            return
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = filename_prefix or f"{review_type}_data"
        
        try:
            if format_type == "CSV":
                self._export_csv(df, f"{base_name}_{timestamp}")
            elif format_type == "Excel":
                self._export_excel(df, f"{base_name}_{timestamp}", review_type)
            elif format_type == "JSON":
                self._export_json(df, f"{base_name}_{timestamp}")
            else:
                st.error(f"❌ 不支持的导出格式: {format_type}")
        
        except Exception as e:
            logger.error(f"导出数据失败: {str(e)}")
            st.error(f"❌ 导出失败: {str(e)}")
    
    def _export_csv(self, df: pd.DataFrame, filename: str):
        """导出CSV格式"""
        try:
            # 处理数据，确保CSV兼容性
            export_df = self._prepare_data_for_export(df)
            csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')
            
            st.download_button(
                label="📥 下载CSV文件",
                data=csv_data,
                file_name=f"{filename}.csv",
                mime="text/csv",
                help="下载CSV格式的数据文件"
            )
            
            # 显示预览
            with st.expander("👁️ CSV预览", expanded=False):
                st.text(csv_data[:1000] + "..." if len(csv_data) > 1000 else csv_data)
                
        except Exception as e:
            raise Exception(f"CSV导出失败: {str(e)}")
    
    def _export_excel(self, df: pd.DataFrame, filename: str, review_type: str):
        """导出Excel格式"""
        try:
            output = BytesIO()
            
            # 准备数据
            export_df = self._prepare_data_for_export(df)
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 主数据表
                export_df.to_excel(writer, index=False, sheet_name='数据详情')
                
                # 统计摘要表
                summary_data = self._generate_summary_data(df, review_type)
                summary_df = pd.DataFrame(summary_data.items(), columns=['指标', '数值'])
                summary_df.to_excel(writer, index=False, sheet_name='统计摘要')
                
                # 如果有作者数据，创建作者统计表
                if 'author' in df.columns:
                    author_stats = df['author'].value_counts().reset_index()
                    author_stats.columns = ['作者', '提交数量']
                    author_stats.to_excel(writer, index=False, sheet_name='作者统计')
                
                # 如果有项目数据，创建项目统计表
                if 'project_name' in df.columns:
                    project_stats = df['project_name'].value_counts().reset_index()
                    project_stats.columns = ['项目', '记录数量']
                    project_stats.to_excel(writer, index=False, sheet_name='项目统计')
            
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 下载Excel文件",
                data=excel_data,
                file_name=f"{filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="下载Excel格式的数据文件（包含多个工作表）"
            )
            
            # 显示Excel内容概览
            with st.expander("👁️ Excel内容概览", expanded=False):
                st.write("📋 **包含的工作表:**")
                st.write("• 数据详情 - 完整的原始数据")
                st.write("• 统计摘要 - 关键指标汇总")
                if 'author' in df.columns:
                    st.write("• 作者统计 - 各作者提交统计")
                if 'project_name' in df.columns:
                    st.write("• 项目统计 - 各项目记录统计")
                
        except Exception as e:
            raise Exception(f"Excel导出失败: {str(e)}")
    
    def _export_json(self, df: pd.DataFrame, filename: str):
        """导出JSON格式"""
        try:
            # 准备数据
            export_df = self._prepare_data_for_export(df)
            
            # 转换为JSON
            json_data = {
                'metadata': {
                    'export_time': datetime.now().isoformat(),
                    'total_records': len(export_df),
                    'columns': list(export_df.columns)
                },
                'data': export_df.to_dict('records')
            }
            
            json_str = json.dumps(json_data, ensure_ascii=False, indent=2, default=str)
            
            st.download_button(
                label="📥 下载JSON文件",
                data=json_str,
                file_name=f"{filename}.json",
                mime="application/json",
                help="下载JSON格式的数据文件"
            )
            
            # 显示JSON预览
            with st.expander("👁️ JSON预览", expanded=False):
                preview_data = {
                    'metadata': json_data['metadata'],
                    'data': json_data['data'][:3] + ['...'] if len(json_data['data']) > 3 else json_data['data']
                }
                st.json(preview_data)
                
        except Exception as e:
            raise Exception(f"JSON导出失败: {str(e)}")
    
    def _prepare_data_for_export(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备导出数据"""
        export_df = df.copy()
        
        # 处理时间字段
        for col in export_df.columns:
            if 'datetime' in col.lower() or 'time' in col.lower() or col in ['reviewed_at', 'created_at', 'updated_at']:
                if col in export_df.columns:
                    try:
                        # 尝试转换为标准时间格式
                        if pd.api.types.is_numeric_dtype(export_df[col]):
                            export_df[col] = pd.to_datetime(export_df[col], unit='s', errors='coerce')
                        else:
                            export_df[col] = pd.to_datetime(export_df[col], errors='coerce')
                        
                        # 格式化为字符串
                        export_df[col] = export_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        # 如果转换失败，保持原值
                        pass
        
        # 处理NaN值
        export_df = export_df.fillna('')
        
        # 重新排列列顺序，把关键信息放在前面
        key_columns = ['author', 'project_name', 'score', 'datetime', 'reviewed_at']
        other_columns = [col for col in export_df.columns if col not in key_columns]
        existing_key_columns = [col for col in key_columns if col in export_df.columns]
        
        export_df = export_df[existing_key_columns + other_columns]
        
        return export_df
    
    def _generate_summary_data(self, df: pd.DataFrame, review_type: str) -> Dict[str, Any]:
        """生成统计摘要数据"""
        summary = {
            '数据类型': review_type.upper(),
            '总记录数': len(df),
            '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 添加具体统计
        if 'score' in df.columns and df['score'].notna().any():
            summary['平均评分'] = f"{df['score'].mean():.2f}"
            summary['最高评分'] = f"{df['score'].max():.2f}"
            summary['最低评分'] = f"{df['score'].min():.2f}"
        
        if 'author' in df.columns:
            summary['参与作者数'] = df['author'].nunique()
            summary['最活跃作者'] = df['author'].value_counts().index[0] if not df['author'].value_counts().empty else 'N/A'
        
        if 'project_name' in df.columns:
            summary['涉及项目数'] = df['project_name'].nunique()
            summary['最活跃项目'] = df['project_name'].value_counts().index[0] if not df['project_name'].value_counts().empty else 'N/A'
        
        # 代码变更统计
        additions_col = 'additions' if 'additions' in df.columns else 'additions_count'
        deletions_col = 'deletions' if 'deletions' in df.columns else 'deletions_count'
        
        if additions_col in df.columns:
            total_additions = df[additions_col].sum()
            summary['总新增行数'] = f"{total_additions:,}"
        
        if deletions_col in df.columns:
            total_deletions = df[deletions_col].sum()
            summary['总删除行数'] = f"{total_deletions:,}"
        
        # 时间范围
        if 'datetime' in df.columns and df['datetime'].notna().any():
            summary['数据时间范围'] = f"{df['datetime'].min()} 至 {df['datetime'].max()}"
            summary['数据跨度天数'] = (df['datetime'].max() - df['datetime'].min()).days
        
        return summary
    
    def show_export_panel(self, df: pd.DataFrame, review_type: str):
        """显示导出面板"""
        if df.empty:
            st.info("📥 暂无数据可导出")
            return
        
        st.markdown("### 📥 数据导出")
        
        export_col1, export_col2, export_col3 = st.columns(3)
        
        with export_col1:
            format_type = st.selectbox(
                "选择导出格式",
                options=self.supported_formats,
                help="选择要导出的文件格式"
            )
        
        with export_col2:
            filename_prefix = st.text_input(
                "文件名前缀",
                value=f"{review_type}_data",
                help="自定义导出文件的名称前缀"
            )
        
        with export_col3:
            st.write("") # 占位符
            st.write("") # 占位符
            if st.button("🚀 开始导出", type="primary"):
                self.export_data(df, format_type, review_type, filename_prefix)
        
        # 显示导出信息
        st.markdown("---")
        export_info_col1, export_info_col2 = st.columns(2)
        
        with export_info_col1:
            st.markdown("**📊 导出数据概览:**")
            st.write(f"• 记录数量: {len(df):,}")
            st.write(f"• 字段数量: {len(df.columns)}")
            st.write(f"• 数据类型: {review_type.upper()}")
        
        with export_info_col2:
            st.markdown("**📋 格式说明:**")
            format_descriptions = {
                'CSV': '逗号分隔值，适合Excel打开',
                'Excel': '多工作表格式，包含统计信息',
                'JSON': '结构化数据，适合程序处理'
            }
            
            for fmt, desc in format_descriptions.items():
                st.write(f"• **{fmt}**: {desc}")
    
    def batch_export(self, data_dict: Dict[str, pd.DataFrame], formats: List[str] = ['Excel']):
        """批量导出多个数据源"""
        if not data_dict:
            st.warning("📥 没有数据可以批量导出")
            return
        
        st.markdown("### 📦 批量导出")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for format_type in formats:
            if format_type == 'Excel':
                # 创建包含所有数据源的Excel文件
                output = BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 写入每个数据源
                    for source_name, df in data_dict.items():
                        if not df.empty:
                            export_df = self._prepare_data_for_export(df)
                            export_df.to_excel(writer, index=False, sheet_name=source_name)
                    
                    # 创建汇总表
                    summary_data = []
                    for source_name, df in data_dict.items():
                        summary_data.append({
                            '数据源': source_name,
                            '记录数': len(df),
                            '字段数': len(df.columns) if not df.empty else 0,
                            '有数据': '是' if not df.empty else '否'
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, index=False, sheet_name='汇总')                
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📦 下载批量分析报告 (Excel)",
                    data=excel_data, 
                    file_name=f"batch_analysis_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="下载包含所有数据源的批量Excel报告"
                )
                
                # 显示批量导出信息
                with st.expander("👁️ 批量导出内容", expanded=False):
                    st.write("📋 **包含的数据源:**")
                    for source_name, df in data_dict.items():
                        status = "✅ 有数据" if not df.empty else "❌ 无数据"
                        st.write(f"• {source_name}: {len(df)} 条记录 {status}")
                    st.write("• 汇总 - 所有数据源的统计汇总")
