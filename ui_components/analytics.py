# -*- coding: utf-8 -*-
"""统计分析模块 - 负责数据统计分析和图表生成"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class DisplayConfig:
    """显示配置类"""
    
    # 颜色配置
    COLOR_SCALES = {
        'primary': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'],
        'secondary': ['#6C5CE7', '#A29BFE', '#FD79A8', '#FDCB6E', '#6C5CE7'],
        'comparison': ['#FF7675', '#74B9FF', '#00B894', '#FDCB6E', '#6C5CE7'],
        'gradient': ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
    }
    
    # 图表配置
    CHART_HEIGHT = 400
    CHART_WIDTH = None


class AnalyticsEngine:
    """分析引擎类"""
    
    def __init__(self):
        self.config = DisplayConfig()
    
    def show_statistics_panel(self, df: pd.DataFrame, review_type: str):
        """显示统计面板 - 优化版本"""
        if df.empty:
            st.warning("暂无数据统计")
            return
        
        # 主要统计指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_records = len(df)
            st.metric(
                "📊 总记录数", 
                f"{total_records:,}",
                delta=f"+{total_records}" if total_records > 0 else None
            )
        
        with col2:
            if 'score' in df.columns and df['score'].notna().any():
                avg_score = df['score'].mean()
                st.metric(
                    "⭐ 平均评分", 
                    f"{avg_score:.1f}",
                    delta=f"{avg_score-3:.1f}" if avg_score > 3 else None
                )
            else:
                st.metric("⭐ 平均评分", "N/A")
        
        with col3:
            if 'author' in df.columns:
                unique_authors = df['author'].nunique()
                st.metric(
                    "👥 参与作者", 
                    f"{unique_authors}",
                    delta=f"+{unique_authors}" if unique_authors > 0 else None
                )
            else:
                st.metric("👥 参与作者", "N/A")
        
        with col4:
            if 'project_name' in df.columns:
                unique_projects = df['project_name'].nunique()
                st.metric(
                    "📁 涉及项目", 
                    f"{unique_projects}",
                    delta=f"+{unique_projects}" if unique_projects > 0 else None
                )
            else:
                st.metric("📁 涉及项目", "N/A")
        
        # 详细统计信息
        self._show_detailed_statistics(df, review_type)
    
    def _show_detailed_statistics(self, df: pd.DataFrame, review_type: str):
        """显示详细统计信息"""
        with st.expander("📈 详细统计", expanded=False):
            stat_col1, stat_col2 = st.columns(2)
            
            with stat_col1:
                st.markdown("**代码变更统计**")
                if 'additions' in df.columns or 'additions_count' in df.columns:
                    additions = df.get('additions', df.get('additions_count', pd.Series([0]))).sum()
                    st.write(f"🟢 总新增行数: {additions:,}")
                
                if 'deletions' in df.columns or 'deletions_count' in df.columns:
                    deletions = df.get('deletions', df.get('deletions_count', pd.Series([0]))).sum()
                    st.write(f"🔴 总删除行数: {deletions:,}")
                
                if 'files_changed' in df.columns:
                    files_changed = df['files_changed'].sum()
                    st.write(f"📄 总变更文件: {files_changed:,}")
            
            with stat_col2:
                st.markdown("**时间统计**")
                if 'datetime' in df.columns and df['datetime'].notna().any():
                    date_range = df['datetime'].max() - df['datetime'].min()
                    st.write(f"📅 数据时间跨度: {date_range.days} 天")
                    st.write(f"📅 最早记录: {df['datetime'].min().strftime('%Y-%m-%d')}")
                    st.write(f"📅 最新记录: {df['datetime'].max().strftime('%Y-%m-%d')}")
                else:
                    st.write("📅 时间信息: 不可用")
    
    def show_charts_analysis(self, df: pd.DataFrame, review_type: str):
        """显示图表分析 - 优化版本"""
        if df.empty:
            st.info("暂无数据可分析")
            return
        
        st.markdown("### 📊 数据分析图表")
        
        # 选择图表类型
        chart_tabs = st.tabs(["📈 趋势分析", "👥 作者分析", "📁 项目分析", "🔍 详细洞察"])
        
        with chart_tabs[0]:
            self._show_trend_analysis(df)
        
        with chart_tabs[1]:
            self._show_author_analysis(df)
        
        with chart_tabs[2]:
            self._show_project_analysis(df)
        
        with chart_tabs[3]:
            self._show_detailed_insights(df)
    
    def _show_trend_analysis(self, df: pd.DataFrame):
        """显示趋势分析"""
        st.markdown("#### 📈 时间趋势分析")
        
        if 'datetime' in df.columns and df['datetime'].notna().sum() > 0:
            # 时间趋势图
            trend_col1, trend_col2 = st.columns(2)
            
            with trend_col1:
                # 每日提交趋势
                df_time = df[df['datetime'].notna()].copy()
                df_time['date'] = df_time['datetime'].dt.date
                daily_counts = df_time.groupby('date').size().reset_index(name='count')
                
                if len(daily_counts) > 1:
                    fig_daily = px.line(
                        daily_counts,
                        x='date',
                        y='count',
                        title="每日提交趋势",
                        markers=True,
                        color_discrete_sequence=self.config.COLOR_SCALES['primary']
                    )
                    fig_daily.update_layout(
                        height=self.config.CHART_HEIGHT,
                        showlegend=False,
                        xaxis_title="日期",
                        yaxis_title="提交数量"
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)
                else:
                    st.info("数据点不足，无法生成趋势图")
            
            with trend_col2:
                # 每周热力图
                if len(df_time) > 7:
                    df_time['weekday'] = df_time['datetime'].dt.day_name()
                    df_time['hour'] = df_time['datetime'].dt.hour
                    heatmap_data = df_time.groupby(['weekday', 'hour']).size().reset_index(name='count')
                    
                    if not heatmap_data.empty:
                        fig_heatmap = px.density_heatmap(
                            heatmap_data,
                            x='hour',
                            y='weekday',
                            z='count',
                            title="提交时间热力图",
                            color_continuous_scale=self.config.COLOR_SCALES['gradient']
                        )
                        fig_heatmap.update_layout(height=self.config.CHART_HEIGHT)
                        st.plotly_chart(fig_heatmap, use_container_width=True)
                    else:
                        st.info("数据不足，无法生成热力图")
        else:
            st.info("没有有效的时间数据进行趋势分析")
    
    def _show_author_analysis(self, df: pd.DataFrame):
        """显示作者分析"""
        st.markdown("#### 👥 作者活跃度分析")
        
        if 'author' in df.columns:
            author_col1, author_col2 = st.columns(2)
            
            with author_col1:
                # 作者提交数量排行
                author_counts = df['author'].value_counts().head(15)
                if not author_counts.empty:
                    fig_authors = px.bar(
                        x=author_counts.values,
                        y=author_counts.index,
                        orientation='h',
                        title="作者贡献排行 (Top 15)",
                        color=author_counts.values,
                        color_continuous_scale=self.config.COLOR_SCALES['primary']
                    )
                    fig_authors.update_layout(
                        height=self.config.CHART_HEIGHT,
                        yaxis={'categoryorder': 'total ascending'},
                        xaxis_title="提交数量",
                        yaxis_title="作者",
                        showlegend=False
                    )
                    st.plotly_chart(fig_authors, use_container_width=True)
            
            with author_col2:
                # 作者评分分布（如果有评分数据）
                if 'score' in df.columns and df['score'].notna().any():
                    author_scores = df.groupby('author')['score'].mean().sort_values(ascending=False).head(10)
                    if not author_scores.empty:
                        fig_scores = px.bar(
                            x=author_scores.index,
                            y=author_scores.values,
                            title="作者平均评分 (Top 10)",
                            color=author_scores.values,
                            color_continuous_scale=self.config.COLOR_SCALES['secondary']
                        )
                        fig_scores.update_layout(
                            height=self.config.CHART_HEIGHT,
                            xaxis_title="作者",
                            yaxis_title="平均评分",
                            showlegend=False
                        )
                        fig_scores.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_scores, use_container_width=True)
                else:
                    st.info("没有评分数据进行分析")
        else:
            st.info("没有作者数据进行分析")
    
    def _show_project_analysis(self, df: pd.DataFrame):
        """显示项目分析"""
        st.markdown("#### 📁 项目分布分析")
        
        if 'project_name' in df.columns:
            project_col1, project_col2 = st.columns(2)
            
            with project_col1:
                # 项目数据分布饼图
                project_counts = df['project_name'].value_counts().head(10)
                if not project_counts.empty:
                    fig_projects = px.pie(
                        values=project_counts.values,
                        names=project_counts.index,
                        title="项目数据分布 (Top 10)",
                        color_discrete_sequence=self.config.COLOR_SCALES['secondary']
                    )
                    fig_projects.update_layout(height=self.config.CHART_HEIGHT)
                    st.plotly_chart(fig_projects, use_container_width=True)
            
            with project_col2:
                # 项目活跃度时间线
                if 'datetime' in df.columns and df['datetime'].notna().any():
                    project_timeline = df[df['datetime'].notna()].groupby([
                        df['datetime'].dt.date, 'project_name'
                    ]).size().reset_index(name='count')
                    
                    if len(project_timeline) > 0:
                        # 只显示top 5项目的时间线
                        top_projects = project_counts.head(5).index.tolist()
                        project_timeline_filtered = project_timeline[
                            project_timeline['project_name'].isin(top_projects)
                        ]
                        
                        if not project_timeline_filtered.empty:
                            fig_timeline = px.line(
                                project_timeline_filtered,
                                x='datetime',
                                y='count',
                                color='project_name',
                                title="项目活跃度时间线 (Top 5)",
                                color_discrete_sequence=self.config.COLOR_SCALES['comparison']
                            )
                            fig_timeline.update_layout(
                                height=self.config.CHART_HEIGHT,
                                xaxis_title="日期",
                                yaxis_title="提交数量"
                            )
                            st.plotly_chart(fig_timeline, use_container_width=True)
                else:
                    st.info("没有时间数据显示项目时间线")
        else:
            st.info("没有项目数据进行分析")
    
    def _show_detailed_insights(self, df: pd.DataFrame):
        """显示详细洞察"""
        st.markdown("#### 🔍 深度数据洞察")
        
        insight_col1, insight_col2 = st.columns(2)
        
        with insight_col1:
            # 代码变更分析
            if any(col in df.columns for col in ['additions', 'deletions', 'additions_count', 'deletions_count']):
                st.markdown("**代码变更分析**")
                
                additions = df.get('additions', df.get('additions_count', pd.Series([0]))).fillna(0)
                deletions = df.get('deletions', df.get('deletions_count', pd.Series([0]))).fillna(0)
                
                if additions.sum() > 0 or deletions.sum() > 0:
                    # 创建变更分布直方图
                    fig_changes = go.Figure()
                    fig_changes.add_trace(go.Histogram(
                        x=additions,
                        name="新增行数",
                        marker_color=self.config.COLOR_SCALES['primary'][0],
                        opacity=0.7
                    ))
                    fig_changes.add_trace(go.Histogram(
                        x=deletions,
                        name="删除行数", 
                        marker_color=self.config.COLOR_SCALES['primary'][1],
                        opacity=0.7
                    ))
                    fig_changes.update_layout(
                        title="代码变更分布",
                        xaxis_title="行数",
                        yaxis_title="频次",
                        height=300,
                        barmode='overlay'
                    )
                    st.plotly_chart(fig_changes, use_container_width=True)
        
        with insight_col2:
            # 评分分布分析
            if 'score' in df.columns and df['score'].notna().any():
                st.markdown("**评分分布分析**")
                
                scores = df['score'].dropna()
                if len(scores) > 0:
                    fig_score_dist = px.histogram(
                        x=scores,
                        nbins=20,
                        title="评分分布直方图",
                        color_discrete_sequence=self.config.COLOR_SCALES['secondary']
                    )
                    fig_score_dist.update_layout(
                        height=300,
                        xaxis_title="评分",
                        yaxis_title="频次"
                    )
                    st.plotly_chart(fig_score_dist, use_container_width=True)
                    
                    # 评分统计信息
                    st.write(f"📊 评分统计:")
                    st.write(f"• 平均分: {scores.mean():.2f}")
                    st.write(f"• 中位数: {scores.median():.2f}")
                    st.write(f"• 标准差: {scores.std():.2f}")
                    st.write(f"• 最高分: {scores.max():.2f}")
                    st.write(f"• 最低分: {scores.min():.2f}")
    
    def generate_comparison_analysis(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """生成对比分析数据"""
        comparison_data = {}
        
        for source_name, df in data_dict.items():
            if df.empty:
                comparison_data[source_name] = {
                    '记录数': 0,
                    '平均评分': 0,
                    '总新增行': 0,
                    '总删除行': 0,
                    '参与作者': 0,
                    '涉及项目': 0
                }
            else:
                comparison_data[source_name] = {
                    '记录数': len(df),
                    '平均评分': df['score'].mean() if 'score' in df.columns and df['score'].notna().any() else 0,
                    '总新增行': df.get('additions', df.get('additions_count', pd.Series([0]))).sum(),
                    '总删除行': df.get('deletions', df.get('deletions_count', pd.Series([0]))).sum(),
                    '参与作者': df['author'].nunique() if 'author' in df.columns else 0,
                    '涉及项目': df['project_name'].nunique() if 'project_name' in df.columns else 0
                }
        
        return comparison_data
    
    def show_comparison_charts(self, comparison_df: pd.DataFrame):
        """显示对比图表"""
        if comparison_df.empty:
            return
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # 记录数对比
            fig_records = px.bar(
                x=comparison_df.index,
                y=comparison_df['记录数'],
                title="📊 记录数对比",
                color=comparison_df.index,
                color_discrete_sequence=self.config.COLOR_SCALES['comparison']
            )
            fig_records.update_layout(
                height=self.config.CHART_HEIGHT,
                showlegend=False,
                xaxis_title="数据源",
                yaxis_title="记录数"
            )
            st.plotly_chart(fig_records, use_container_width=True)
        
        with chart_col2:
            # 平均评分对比
            fig_score = px.bar(
                x=comparison_df.index,
                y=comparison_df['平均评分'],
                title="⭐ 平均评分对比",
                color=comparison_df.index,
                color_discrete_sequence=self.config.COLOR_SCALES['comparison']
            )
            fig_score.update_layout(
                height=self.config.CHART_HEIGHT,
                showlegend=False,
                xaxis_title="数据源",
                yaxis_title="平均评分"
            )
            st.plotly_chart(fig_score, use_container_width=True)
