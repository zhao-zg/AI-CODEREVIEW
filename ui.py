#!/usr/bin/env python3
"""
多类型代码审查UI - 支持SVN、GitLab、GitHub
"""

import datetime
import json
import math
import os
import sys
import tempfile
import hashlib

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib
from biz.service.review_service import ReviewService
from biz.utils.config_manager import ConfigManager

# 导入配置文件
try:
    from conf.dashboard_config import *
except ImportError:
    # 如果配置文件不存在，使用默认值
    DASHBOARD_TITLE = "AI-CodeReview 代码审查仪表板"
    DASHBOARD_ICON = "🤖"
    DASHBOARD_LAYOUT = "wide"
    CHART_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57"]
    MAX_RECORDS_PER_PAGE = 100
    DEFAULT_CHART_HEIGHT = 400

# Streamlit 配置 - 必须在所有其他 Streamlit 命令之前
st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon=DASHBOARD_ICON,
    layout=DASHBOARD_LAYOUT,
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>    /* 主要布局 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* 顶部用户工具栏 */
    .user-toolbar {
        position: fixed;
        top: 0;
        right: 0;
        z-index: 1000;
        background: rgba(102, 126, 234, 0.95);
        padding: 0.5rem 1rem;
        border-radius: 0 0 0 15px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .user-dropdown {
        position: relative;
        display: inline-block;
    }
    
    .user-dropdown-content {
        display: none;
        position: absolute;
        right: 0;
        background-color: white;
        min-width: 200px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        z-index: 1;
        border-radius: 8px;
        padding: 0.5rem;
    }
    
    .user-dropdown:hover .user-dropdown-content {
        display: block;
    }
    
    .user-info {
        color: white;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .user-info:hover {
        background: rgba(255,255,255,0.1);
    }
    
    /* 标题样式 */
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    /* 卡片样式 */
    .config-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    
    /* 表单样式 */
    .stForm {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    
    /* 选项卡样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 20px;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0px 0px;
        color: #262730;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
    }
    
    /* 按钮样式 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 45px;
        font-weight: 500;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
      /* 指标卡片 */
    [data-testid="metric-container"] {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* 折叠面板优化 */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.5rem;
        border: 1px solid #e9ecef;
    }
    
    .streamlit-expanderContent {
        background: white;
        border-radius: 0 0 8px 8px;
        border: 1px solid #e9ecef;
        border-top: none;
    }
    
    /* 右上角用户工具栏样式 */
    .user-toolbar {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 1000;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        padding: 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        backdrop-filter: blur(10px);
    }
    
    /* 配置卡片样式 */
    .config-section {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* 数据框样式 */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* 进度条样式 */
    .stProgress .st-bo {
        background-color: #e9ecef;
        border-radius: 10px;
    }
    
    .stProgress .st-bp {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置matplotlib中文字体支持
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

load_dotenv("conf/.env")

# 从环境变量中读取用户名和密码
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}

# 工具函数
def authenticate(username, password):
    """登录验证函数"""
    return username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password

def get_available_authors(review_types):
    """获取可用的作者列表"""
    try:
        service = ReviewService()
        authors = set()
        
        if 'svn' in review_types or 'github' in review_types or 'gitlab' in review_types:
            df = service.get_version_tracking_logs(review_types=review_types)
            if not df.empty:
                authors.update(df['author'].dropna().unique())
                
        return sorted(list(authors))
    except Exception as e:
        st.error(f"获取作者列表失败: {e}")
        return []

def get_available_projects(review_types):
    """获取可用的项目列表"""
    try:
        service = ReviewService()
        projects = set()
        
        if 'svn' in review_types or 'github' in review_types or 'gitlab' in review_types:
            df = service.get_version_tracking_logs(review_types=review_types)
            if not df.empty:
                projects.update(df['project_name'].dropna().unique())
                
        return sorted(list(projects))
    except Exception as e:
        st.error(f"获取项目列表失败: {e}")
        return []

def format_timestamp(timestamp):
    """格式化时间戳"""
    try:
        if pd.isna(timestamp) or timestamp == 0:
            return "未知"
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(timestamp)

def display_version_tracking_data(review_type, authors=None, projects=None, date_range=None, score_range=(0, 100)):
    """显示版本跟踪数据"""
    try:
        service = ReviewService()
        
        # 处理日期范围
        updated_at_gte = None
        updated_at_lte = None
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            updated_at_gte = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
            updated_at_lte = int(datetime.datetime.combine(end_date, datetime.time.max).timestamp())
        elif date_range and len(date_range) == 1:
            start_date = date_range[0]
            updated_at_gte = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
            updated_at_lte = int(datetime.datetime.combine(start_date, datetime.time.max).timestamp())
        
        # 获取数据
        df = service.get_version_tracking_logs(
            authors=authors if authors else None,
            project_names=projects if projects else None,
            updated_at_gte=updated_at_gte,
            updated_at_lte=updated_at_lte,
            review_types=[review_type]
        )
        
        if df.empty:
            st.info(f"📭 暂无 {review_type.upper()} 类型的审查数据")
            return
        
        # 过滤分数范围
        df = df[(df['score'] >= score_range[0]) & (df['score'] <= score_range[1])]
        
        # 格式化时间戳
        df['formatted_time'] = df['updated_at'].apply(format_timestamp)
        
        # 数据概览
        st.markdown("##### 📊 数据概览")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📋 总记录数", len(df))
        
        with col2:
            if not df.empty:
                avg_score = df['score'].mean()
                st.metric("⭐ 平均分数", f"{avg_score:.1f}")
            else:
                st.metric("⭐ 平均分数", "N/A")
        
        with col3:
            unique_projects = df['project_name'].nunique()
            st.metric("📦 项目数", unique_projects)
        
        with col4:
            unique_authors = df['author'].nunique()
            st.metric("👥 开发者数", unique_authors)
        
        # 图表分析
        if not df.empty:
            st.markdown("##### 📈 图表分析")
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # 项目分布图
                st.markdown("**📦 项目审查分布**")
                project_counts = df['project_name'].value_counts()
                if len(project_counts) > 0:
                    fig, ax = plt.subplots(figsize=(8, 6))
                    project_counts.plot(kind='bar', ax=ax, color=CHART_COLORS[0])
                    ax.set_title('项目审查数量分布')
                    ax.set_xlabel('项目名称')
                    ax.set_ylabel('审查次数')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                
            with chart_col2:
                # 分数分布图
                st.markdown("**📊 审查分数分布**")
                if len(df) > 0:
                    fig, ax = plt.subplots(figsize=(8, 6))
                    df['score'].hist(bins=20, ax=ax, color=CHART_COLORS[1], alpha=0.7)
                    ax.set_title('审查分数分布')
                    ax.set_xlabel('分数')
                    ax.set_ylabel('频次')
                    ax.axvline(df['score'].mean(), color='red', linestyle='--', label=f'平均分: {df["score"].mean():.1f}')
                    ax.legend()
                    plt.tight_layout()
                    st.pyplot(fig)
          # 详细数据表格
        st.markdown("##### 📋 详细数据")
        
        # 配置列显示
        if review_type == 'svn':
            display_columns = ['project_name', 'author', 'formatted_time', 'score', 'commit_sha', 'file_paths']
            column_config = {
                "project_name": st.column_config.TextColumn("项目名称", width="medium"),
                "author": st.column_config.TextColumn("作者", width="small"),
                "formatted_time": st.column_config.TextColumn("提交时间", width="medium"),
                "score": st.column_config.ProgressColumn("质量分数", format="%d", min_value=0, max_value=100, width="small"),
                "commit_sha": st.column_config.TextColumn("提交SHA", width="medium"),
                "file_paths": st.column_config.TextColumn("文件路径", width="large"),
            }
        else:
            display_columns = ['project_name', 'author', 'branch', 'formatted_time', 'score', 'commit_sha']
            column_config = {
                "project_name": st.column_config.TextColumn("项目名称", width="medium"),
                "author": st.column_config.TextColumn("作者", width="small"),
                "branch": st.column_config.TextColumn("分支", width="small"),
                "formatted_time": st.column_config.TextColumn("提交时间", width="medium"),
                "score": st.column_config.ProgressColumn("质量分数", format="%d", min_value=0, max_value=100, width="small"),
                "commit_sha": st.column_config.TextColumn("提交SHA", width="medium"),
            }
        
        # 分页显示
        page_size = st.slider("每页显示条数", 10, 100, 20, 10)
        total_pages = math.ceil(len(df) / page_size)
        
        if total_pages > 1:
            page = st.selectbox("选择页码", range(1, total_pages + 1), format_func=lambda x: f"第 {x} 页")
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            display_df = df[display_columns].iloc[start_idx:end_idx]
            current_page_df = df.iloc[start_idx:end_idx]
        else:
            display_df = df[display_columns]
            current_page_df = df
        
        # 显示数据表格
        event = st.dataframe(
            display_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # 处理行选择事件，显示详细审查结果
        if event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            if selected_row_idx < len(current_page_df):
                selected_record = current_page_df.iloc[selected_row_idx]
                
                st.markdown("---")
                st.markdown("### 🔍 审查结果详情")
                
                # 基本信息
                detail_col1, detail_col2, detail_col3 = st.columns(3)
                with detail_col1:
                    st.markdown(f"**📦 项目名称:** {selected_record['project_name']}")
                    st.markdown(f"**👤 作者:** {selected_record['author']}")
                with detail_col2:
                    st.markdown(f"**📅 审查时间:** {selected_record['formatted_time']}")
                    st.markdown(f"**⭐ 质量分数:** {selected_record['score']}")
                with detail_col3:
                    st.markdown(f"**🔗 提交SHA:** `{selected_record['commit_sha'][:12]}...`")
                    if review_type == 'svn':
                        try:
                            import json
                            file_paths = json.loads(selected_record['file_paths']) if selected_record['file_paths'] else []
                            st.markdown(f"**📁 文件数量:** {len(file_paths)}")
                        except:
                            st.markdown(f"**📁 文件路径:** {selected_record['file_paths']}")
                    else:
                        st.markdown(f"**🌿 分支:** {selected_record.get('branch', 'N/A')}")
                
                # 审查结果详情
                st.markdown("#### 📝 详细审查报告")
                
                # 使用expander显示完整的审查结果
                with st.expander("🔍 点击查看完整审查报告", expanded=True):
                    review_result = selected_record.get('commit_messages', '暂无审查结果')
                    
                    # 如果审查结果很长，提供格式化显示
                    if len(str(review_result)) > 500:
                        # 尝试格式化Markdown内容
                        st.markdown(str(review_result))
                    else:
                        st.text(str(review_result))
                
                # 文件变更详情（如果是SVN类型）
                if review_type == 'svn' and selected_record.get('file_paths'):
                    st.markdown("#### 📁 变更文件列表")
                    try:
                        import json
                        file_paths = json.loads(selected_record['file_paths'])
                        if file_paths:
                            for i, file_path in enumerate(file_paths, 1):
                                st.markdown(f"{i}. `{file_path}`")
                        else:
                            st.info("无文件变更信息")
                    except:
                        st.text(selected_record['file_paths'])
                
                # 操作按钮
                action_col1, action_col2, action_col3 = st.columns(3)
                with action_col1:
                    if st.button("📋 复制审查结果", key="copy_result"):
                        st.code(str(review_result), language="markdown")
                        st.success("✅ 审查结果已显示在上方代码框中，可手动复制")
                
                with action_col2:
                    if st.button("📥 导出此条记录", key="export_single"):
                        single_record_df = current_page_df.iloc[[selected_row_idx]]
                        csv = single_record_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="下载单条记录CSV",
                            data=csv,
                            file_name=f"review_detail_{selected_record['commit_sha'][:8]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_single"
                        )
                
                with action_col3:
                    if st.button("🔄 刷新详情", key="refresh_detail"):
                        st.rerun()
        
        else:
            st.info("💡 点击表格中的任意行查看详细审查结果")
        
        # 批量导出功能
        st.markdown("---")
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            if st.button("📥 导出当前页数据", key="export_page"):
                csv = current_page_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载当前页CSV文件",
                    data=csv,
                    file_name=f"{review_type}_review_page_{page if total_pages > 1 else 1}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_page"
                )
        
        with export_col2:
            if st.button("📥 导出全部数据", key="export_all"):
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载全部数据CSV文件",
                    data=csv,
                    file_name=f"{review_type}_review_all_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_all"
                )
            
    except Exception as e:
        st.error(f"显示数据时出错: {e}")

def display_legacy_data(review_type):
    """显示传统的MR/Push数据"""
    current_date = datetime.date.today()
    start_date_default = current_date - datetime.timedelta(days=7)
    
    st.markdown(f"##### 🔍 {review_type.upper()}数据筛选")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        start_date = st.date_input("📅 开始日期", start_date_default, key=f"{review_type}_start_date")
    with col2:
        end_date = st.date_input("📅 结束日期", current_date, key=f"{review_type}_end_date")
    
    start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
    
    service = ReviewService()
    
    # 获取数据
    if review_type == 'mr':
        df = service.get_mr_review_logs(
            updated_at_gte=int(start_datetime.timestamp()),
            updated_at_lte=int(end_datetime.timestamp())
        )
    else:  # push
        df = service.get_push_review_logs(
            updated_at_gte=int(start_datetime.timestamp()),
            updated_at_lte=int(end_datetime.timestamp())
        )
    
    if df.empty:
        st.info(f"📭 指定时间范围内暂无 {review_type.upper()} 数据")
        return
    
    # 获取筛选选项
    unique_authors = sorted(df["author"].dropna().unique().tolist())
    unique_projects = sorted(df["project_name"].dropna().unique().tolist())
    
    with col3:
        authors = st.multiselect("👤 用户名", unique_authors, default=[], key=f"{review_type}_authors")
    with col4:
        project_names = st.multiselect("📁 项目名", unique_projects, default=[], key=f"{review_type}_projects")
    
    # 应用筛选
    if authors:
        df = df[df['author'].isin(authors)]
    if project_names:
        df = df[df['project_name'].isin(project_names)]
    
    # 格式化时间
    df['formatted_time'] = df['updated_at'].apply(format_timestamp)
    
    # 数据概览
    st.markdown("##### 📊 数据概览")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 总记录数", len(df))
    
    with col2:
        if not df.empty:
            avg_score = df['score'].mean()
            st.metric("⭐ 平均分数", f"{avg_score:.1f}")
    
    with col3:
        unique_projects = df['project_name'].nunique()
        st.metric("📦 项目数", unique_projects)
    
    with col4:
        unique_authors = df['author'].nunique()
        st.metric("👥 开发者数", unique_authors)
    
    # 详细数据
    st.markdown("##### 📋 详细数据")
    if not df.empty:
        if review_type == 'mr':
            display_columns = ['project_name', 'author', 'source_branch', 'target_branch', 'formatted_time', 'score', 'url']
            column_config = {
                "project_name": st.column_config.TextColumn("项目名称", width="medium"),
                "author": st.column_config.TextColumn("作者", width="small"),
                "source_branch": st.column_config.TextColumn("源分支", width="small"),
                "target_branch": st.column_config.TextColumn("目标分支", width="small"),
                "formatted_time": st.column_config.TextColumn("更新时间", width="medium"),
                "score": st.column_config.ProgressColumn("质量分数", format="%d", min_value=0, max_value=100, width="small"),
                "url": st.column_config.LinkColumn("链接", max_chars=100, display_text="🔗 查看", width="small"),
            }
        else:  # push
            display_columns = ['project_name', 'author', 'branch', 'formatted_time', 'score']
            column_config = {
                "project_name": st.column_config.TextColumn("项目名称", width="medium"),
                "author": st.column_config.TextColumn("作者", width="small"),
                "branch": st.column_config.TextColumn("分支", width="small"),
                "formatted_time": st.column_config.TextColumn("更新时间", width="medium"),
                "score": st.column_config.ProgressColumn("质量分数", format="%d", min_value=0, max_value=100, width="small"),
            }
          # 分页显示
        page_size = st.slider("每页显示条数", 10, 100, 20, 10, key=f"{review_type}_page_size")
        total_pages = math.ceil(len(df) / page_size)
        
        if total_pages > 1:
            page = st.selectbox("选择页码", range(1, total_pages + 1), format_func=lambda x: f"第 {x} 页", key=f"{review_type}_page")
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            display_df = df[display_columns].iloc[start_idx:end_idx]
            current_page_df = df.iloc[start_idx:end_idx]
        else:
            display_df = df[display_columns]
            current_page_df = df
        
        # 显示数据表格
        event = st.dataframe(
            display_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # 处理行选择事件，显示详细审查结果
        if event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            if selected_row_idx < len(current_page_df):
                selected_record = current_page_df.iloc[selected_row_idx]
                
                st.markdown("---")
                st.markdown("### 🔍 审查结果详情")
                
                # 基本信息
                detail_col1, detail_col2, detail_col3 = st.columns(3)
                with detail_col1:
                    st.markdown(f"**📦 项目名称:** {selected_record['project_name']}")
                    st.markdown(f"**👤 作者:** {selected_record['author']}")
                with detail_col2:
                    st.markdown(f"**📅 更新时间:** {selected_record['formatted_time']}")
                    st.markdown(f"**⭐ 质量分数:** {selected_record['score']}")
                with detail_col3:
                    if review_type == 'mr':
                        st.markdown(f"**🌿 源分支:** {selected_record['source_branch']}")
                        st.markdown(f"**🎯 目标分支:** {selected_record['target_branch']}")
                        if selected_record.get('url'):
                            st.markdown(f"**🔗 链接:** [查看MR]({selected_record['url']})")
                    else:  # push
                        st.markdown(f"**🌿 分支:** {selected_record.get('branch', 'N/A')}")
                
                # 审查结果详情
                st.markdown("#### 📝 详细审查报告")
                
                # 使用expander显示完整的审查结果
                with st.expander("🔍 点击查看完整审查报告", expanded=True):
                    review_result = selected_record.get('commit_messages', '暂无审查结果')
                    
                    # 如果审查结果很长，提供格式化显示
                    if len(str(review_result)) > 500:
                        # 尝试格式化Markdown内容
                        st.markdown(str(review_result))
                    else:
                        st.text(str(review_result))
                
                # 变更统计（如果有相关数据）
                if 'additions' in selected_record and 'deletions' in selected_record:
                    st.markdown("#### 📊 代码变更统计")
                    change_col1, change_col2, change_col3 = st.columns(3)
                    with change_col1:
                        st.metric("➕ 新增行数", selected_record.get('additions', 0))
                    with change_col2:
                        st.metric("➖ 删除行数", selected_record.get('deletions', 0))
                    with change_col3:
                        total_changes = (selected_record.get('additions', 0) + selected_record.get('deletions', 0))
                        st.metric("📈 总变更行数", total_changes)
                
                # 操作按钮
                action_col1, action_col2, action_col3 = st.columns(3)
                with action_col1:
                    if st.button("📋 复制审查结果", key=f"copy_result_{review_type}"):
                        st.code(str(review_result), language="markdown")
                        st.success("✅ 审查结果已显示在上方代码框中，可手动复制")
                
                with action_col2:
                    if st.button("📥 导出此条记录", key=f"export_single_{review_type}"):
                        single_record_df = current_page_df.iloc[[selected_row_idx]]
                        csv = single_record_df.to_csv(index=False, encoding='utf-8-sig')
                        record_id = selected_record.get('id', f"{review_type}_{selected_row_idx}")
                        st.download_button(
                            label="下载单条记录CSV",
                            data=csv,
                            file_name=f"{review_type}_detail_{record_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key=f"download_single_{review_type}"
                        )
                
                with action_col3:
                    if st.button("🔄 刷新详情", key=f"refresh_detail_{review_type}"):
                        st.rerun()
        
        else:
            st.info("💡 点击表格中的任意行查看详细审查结果")
        
        # 批量导出功能
        st.markdown("---")
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            if st.button("📥 导出当前页数据", key=f"export_page_{review_type}"):
                csv = current_page_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载当前页CSV文件",
                    data=csv,
                    file_name=f"{review_type}_review_page_{page if total_pages > 1 else 1}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key=f"download_page_{review_type}"
                )
        
        with export_col2:
            if st.button("📥 导出全部数据", key=f"export_all_{review_type}"):
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载全部数据CSV文件",
                    data=csv,
                    file_name=f"{review_type}_review_all_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key=f"download_all_{review_type}"
                )

def login_page():
    """登录页面"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1>🤖 AI-CodeReview 代码审查仪表板</h1>
        <p>请输入您的登录凭据</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("👤 用户名")
            password = st.text_input("🔒 密码", type="password")
            submitted = st.form_submit_button("🚪 登录", use_container_width=True)
        
        if submitted:
            if authenticate(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                
                # 保存登录状态
                save_login_state(username)
                
                # 设置URL参数以支持session持久化
                st.query_params["auto_login"] = "true"
                st.query_params["user"] = username
                
                st.success("✅ 登录成功！")
                st.rerun()
            else:
                st.error("❌ 用户名或密码错误！")

def main_dashboard():
    """主仪表板"""
    
    # 右上角用户信息显示
    if "username" in st.session_state:
        # 使用列布局在右上角显示用户信息和操作按钮
        col_left, col_center, col_right = st.columns([3, 1, 1])
        
        with col_right:
            # 创建一个容器来放置用户操作
            with st.container():
                st.markdown(f"""
                <div style="text-align: right; padding: 0.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            border-radius: 10px; color: white; margin-bottom: 1rem;">
                    <small>👤 {st.session_state['username']}</small>
                </div>
                """, unsafe_allow_html=True)
                  # 操作按钮
                col_refresh, col_logout = st.columns([1, 1])
                with col_refresh:
                    if st.button("🔄", help="刷新数据", key="refresh_top"):
                        st.cache_data.clear()
                        st.rerun()
                
                with col_logout:
                    if st.button("🚪", help="注销登录", key="logout_top"):
                        st.session_state["authenticated"] = False
                        st.session_state.pop("username", None)
                        
                        # 清理URL参数
                        if "auto_login" in st.query_params:
                            del st.query_params["auto_login"]
                        if "user" in st.query_params:
                            del st.query_params["user"]
                        
                        # 清除登录状态
                        clear_login_state()
                        
                        st.rerun()
    
    # 页面标题 - 使用更现代的设计
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 600;">🤖 AI-CodeReview 代码审查仪表板</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">智能代码质量监控与多平台审查分析系统</p>
        <div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.8;">
            支持 SVN • GitLab • GitHub • 多种AI模型
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 侧边栏 - 简化布局
    with st.sidebar:        
        # 功能菜单
        st.markdown("### 🛠️ 系统功能")
        
        # 页面导航 - 使用更直观的布局
        page = st.radio(
            "选择功能模块",
            ["📊 数据分析", "⚙️ 配置管理"],
            key="page_selector",
            help="选择要访问的功能模块"
        )
        
        st.markdown("---")
        
        # 系统信息
        st.markdown("### ℹ️ 系统信息")
        
        # 获取系统状态
        try:
            config_manager = ConfigManager()
            env_config = config_manager.get_env_config()
            configured_count = len([v for v in env_config.values() if v and v.strip()])
            total_count = len(env_config)
            
            st.metric("配置完成度", f"{configured_count}/{total_count}")
            st.metric("当前AI模型", env_config.get("LLM_PROVIDER", "未配置"))
        except:
            st.info("配置信息加载中...")
        
        # 帮助信息
        st.markdown("---")
        with st.expander("📖 使用帮助"):
            st.markdown("""
            **数据分析**: 查看代码审查统计和详细记录
            
            **配置管理**: 管理AI模型、平台开关等系统配置
            
            **快速操作**: 
            - 🔄 刷新所有数据缓存（右上角）
            - 🚪 安全退出系统（右上角）
            """)
    
    # 根据选择的页面显示内容
    if page == "⚙️ 配置管理":
        env_management_page()
    else:
        data_analysis_page()

def data_analysis_page():
    """数据分析页面"""
    # 页面标题
    st.markdown("""
    <div class="config-card">
        <h2 style="margin: 0; color: #2c3e50;">� 代码审查数据分析</h2>
        <p style="margin: 0.5rem 0 0 0; color: #7f8c8d;">分析代码审查数据，洞察代码质量趋势</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 获取平台开关配置
    config_manager = ConfigManager()
    try:
        env_config = config_manager.get_env_config()
        svn_enabled = env_config.get("SVN_CHECK_ENABLED", "0") == "1"
        gitlab_enabled = env_config.get("GITLAB_ENABLED", "1") == "1"
        github_enabled = env_config.get("GITHUB_ENABLED", "1") == "1"
    except:
        # 默认全部启用
        svn_enabled = True
        gitlab_enabled = True
        github_enabled = True
    
    # 获取审查类型统计
    review_stats = ReviewService().get_review_type_stats()
    
    # 构建可用类型列表
    available_types = []
    type_labels = {}
    
    # 检查各种类型的数据，考虑开关状态
    if gitlab_enabled and review_stats.get('mr_count', 0) > 0:
        available_types.append('mr')
        type_labels['mr'] = f"🔀 GitLab MR ({review_stats['mr_count']} 条)"
    
    if gitlab_enabled and review_stats.get('push_count', 0) > 0:
        available_types.append('push')
        type_labels['push'] = f"📤 GitLab Push ({review_stats['push_count']} 条)"
    
    if svn_enabled and review_stats.get('svn_count', 0) > 0:
        available_types.append('svn')
        type_labels['svn'] = f"📂 SVN 提交 ({review_stats['svn_count']} 条)"
    
    if github_enabled and review_stats.get('github_count', 0) > 0:
        available_types.append('github')
        type_labels['github'] = f"🐙 GitHub ({review_stats['github_count']} 条)"
    
    if gitlab_enabled and review_stats.get('gitlab_count', 0) > 0:
        available_types.append('gitlab')
        type_labels['gitlab'] = f"🦊 GitLab 通用 ({review_stats['gitlab_count']} 条)"
    
    # 如果没有数据，显示已启用的类型选项
    if not available_types:
        if svn_enabled:
            available_types.append('svn')
            type_labels['svn'] = '📂 SVN 提交 (暂无数据)'
        if gitlab_enabled:
            available_types.extend(['mr', 'push', 'gitlab'])
            type_labels.update({
                'mr': '� GitLab MR (暂无数据)',
                'push': '� GitLab Push (暂无数据)',
                'gitlab': '🦊 GitLab 通用 (暂无数据)'
            })
        if github_enabled:
            available_types.append('github')
            type_labels['github'] = '🐙 GitHub (暂无数据)'    # 如果所有平台都被禁用
    if not available_types:
        st.warning("⚠️ 所有代码托管平台都已禁用，请在配置管理中启用至少一个平台。")
        return
    
    # 类型选择区域 - 使用卡片布局
    st.markdown("""
    <div class="config-card">
        <h3 style="margin: 0 0 1rem 0; color: #2c3e50;">🎯 数据源选择</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_review_type = st.selectbox(
            "选择审查数据类型",
            options=available_types,
            format_func=lambda x: type_labels.get(x, x),
            key="main_review_type_selector",
            help="选择要分析的代码审查数据类型"
        )
    
    with col2:
        if st.button("🔄 刷新统计", use_container_width=True, key="refresh_stats", help="刷新数据统计"):
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        # 显示当前选择的平台状态
        if selected_review_type in ['svn'] and svn_enabled:
            st.success("✅ SVN 已启用")
        elif selected_review_type in ['mr', 'push', 'gitlab'] and gitlab_enabled:
            st.success("✅ GitLab 已启用")
        elif selected_review_type in ['github'] and github_enabled:
            st.success("✅ GitHub 已启用")
    
    st.markdown("---")
      # 显示对应的数据
    if selected_review_type in ['mr', 'push']:
        # 传统MR/Push数据
        display_legacy_data(selected_review_type)
    else:
        # 版本跟踪数据（SVN、GitHub、GitLab通用）
        st.markdown("""
        <div class="config-card">
            <h3 style="margin: 0 0 1rem 0; color: #2c3e50;">🔍 数据筛选与分析</h3>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("⚙️ 高级筛选条件", expanded=False):
            st.markdown("**自定义筛选条件，精确分析目标数据**")
            
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                authors = st.multiselect(
                    "👤 开发者筛选", 
                    options=get_available_authors([selected_review_type]), 
                    key="main_author_filter",
                    help="选择特定开发者的提交记录"
                )
                
                date_range = st.date_input(
                    "📅 时间范围",
                    value=None,
                    key="main_date_filter",
                    help="选择要分析的时间范围"
                )
            
            with filter_col2:
                projects = st.multiselect(
                    "📦 项目筛选", 
                    options=get_available_projects([selected_review_type]), 
                    key="main_project_filter",
                    help="选择特定项目进行分析"
                )
                
                score_range = st.slider(
                    "⭐ 分数范围",
                    min_value=0,
                    max_value=100,                    value=(0, 100),
                    key="main_score_filter",
                    help="筛选特定分数范围的审查记录"
                )
        
        # 显示数据
        display_version_tracking_data(
            selected_review_type, 
            authors if authors else None, 
            projects if projects else None, 
            date_range if date_range else None, 
            score_range
        )

def env_management_page():
    """配置管理页面"""
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; margin-bottom: 2rem; color: white; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 2.2rem;">⚙️ 系统配置管理</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;">集中管理所有系统配置，让部署更简单</p>
    </div>
    """, unsafe_allow_html=True)
    
    config_manager = ConfigManager()
      # 创建选项卡
    tab1, tab2, tab3 = st.tabs(["🎛️ 系统配置", "📋 配置总览", "� 配置模板"])
    
    with tab1:
        st.markdown("### 🎛️ 系统配置编辑")
        st.markdown("📝 **配置您的AI代码审查系统**，支持多种AI模型和代码托管平台。")
        
        # 配置进度指示器
        try:
            env_config = config_manager.get_env_config()
            configured_count = len([v for v in env_config.values() if v and v.strip()])
            total_count = len(env_config)
            progress = configured_count / total_count if total_count > 0 else 0
            
            col_progress1, col_progress2, col_progress3 = st.columns([1, 2, 1])
            with col_progress2:
                st.metric("配置完成度", f"{configured_count}/{total_count}", f"{progress:.1%}")
                st.progress(progress)
        except:
            env_config = {}
        
        st.markdown("---")
        
        # 配置编辑表单 - 重新组织排版
        with st.form("env_config_form"):
            # 第一部分：基础核心配置（少量配置项）
            st.markdown("#### 🎯 核心配置")
            col1, col2 = st.columns(2)
            
            with col1:
                llm_provider = st.selectbox(
                    "AI模型供应商", 
                    ["deepseek", "openai", "zhipuai", "qwen", "ollama"],
                    index=["deepseek", "openai", "zhipuai", "qwen", "ollama"].index(env_config.get("LLM_PROVIDER", "deepseek"))
                )
                review_style = st.selectbox(
                    "审查风格", 
                    ["professional", "sarcastic", "gentle", "humorous"],
                    index=["professional", "sarcastic", "gentle", "humorous"].index(env_config.get("REVIEW_STYLE", "professional"))
                )
            
            with col2:
                server_port = st.text_input("服务端口", value=env_config.get("SERVER_PORT", "5001"))
                timezone = st.text_input("时区", value=env_config.get("TZ", "Asia/Shanghai"))
            
            # 第二部分：平台开关配置（少量配置项）
            st.markdown("#### 🔀 平台开关配置")
            col_platform1, col_platform2, col_platform3 = st.columns(3)
            
            with col_platform1:
                svn_enabled = st.checkbox("启用SVN支持", value=env_config.get("SVN_CHECK_ENABLED", "0") == "1", 
                                        help="启用后将在数据分析中显示SVN相关数据")
            
            with col_platform2:
                gitlab_enabled = st.checkbox("启用GitLab支持", value=env_config.get("GITLAB_ENABLED", "1") == "1",
                                           help="启用后将在数据分析中显示GitLab相关数据")
            
            with col_platform3:
                github_enabled = st.checkbox("启用GitHub支持", value=env_config.get("GITHUB_ENABLED", "1") == "1",
                                            help="启用后将在数据分析中显示GitHub相关数据")
            
            # 第三部分：版本控制配置（少量配置项）
            st.markdown("#### 📋 版本控制配置")
            col_version1, col_version2 = st.columns(2)
            
            with col_version1:
                version_tracking_enabled = st.checkbox("启用版本追踪", value=env_config.get("VERSION_TRACKING_ENABLED", "1") == "1")
                reuse_previous_review = st.checkbox("复用之前审查结果", value=env_config.get("REUSE_PREVIOUS_REVIEW_RESULT", "1") == "1")
            
            with col_version2:
                retention_days = st.number_input("版本记录保留天数", 
                                               min_value=1, max_value=365, 
                                               value=int(env_config.get("VERSION_TRACKING_RETENTION_DAYS", "30") or "30"))
                review_max_tokens = st.number_input("Review最大Token数", 
                                                  min_value=1000, max_value=50000, 
                                                  value=int(env_config.get("REVIEW_MAX_TOKENS", "10000")))
            
            # 第四部分：用户权限配置（少量配置项）
            st.markdown("#### 👤 用户权限配置")
            col12, col13 = st.columns(2)
            
            with col12:
                dashboard_user = st.text_input("Dashboard用户名", value=env_config.get("DASHBOARD_USER", "admin"))
            
            with col13:
                dashboard_password = st.text_input("Dashboard密码", value=env_config.get("DASHBOARD_PASSWORD", "admin"), type="password")
            
            # 分隔线
            st.markdown("---")
            
            # 第五部分：AI模型详细配置（多配置项，折叠显示）
            with st.expander("🤖 AI模型详细配置", expanded=False):
                col_ai1, col_ai2 = st.columns(2)
                
                with col_ai1:
                    st.markdown("**DeepSeek 配置**")
                    deepseek_key = st.text_input("DeepSeek API Key", value=env_config.get("DEEPSEEK_API_KEY", ""), type="password")
                    deepseek_base = st.text_input("DeepSeek API Base", value=env_config.get("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com"))
                    deepseek_model = st.text_input("DeepSeek Model", value=env_config.get("DEEPSEEK_API_MODEL", "deepseek-chat"))
                    
                    st.markdown("**OpenAI 配置**")
                    openai_key = st.text_input("OpenAI API Key", value=env_config.get("OPENAI_API_KEY", ""), type="password")
                    openai_base = st.text_input("OpenAI API Base", value=env_config.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1"))
                    openai_model = st.text_input("OpenAI Model", value=env_config.get("OPENAI_API_MODEL", "gpt-4o-mini"))
                
                with col_ai2:
                    st.markdown("**智谱AI 配置**")
                    zhipuai_key = st.text_input("智谱AI API Key", value=env_config.get("ZHIPUAI_API_KEY", ""), type="password")
                    zhipuai_model = st.text_input("智谱AI Model", value=env_config.get("ZHIPUAI_API_MODEL", "GLM-4-Flash"))
                    
                    st.markdown("**Qwen 配置**")
                    qwen_key = st.text_input("Qwen API Key", value=env_config.get("QWEN_API_KEY", ""), type="password")
                    qwen_base = st.text_input("Qwen API Base", value=env_config.get("QWEN_API_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
                    qwen_model = st.text_input("Qwen Model", value=env_config.get("QWEN_API_MODEL", "qwen-coder-plus"))
                    
                    st.markdown("**Ollama 配置**")
                    ollama_base = st.text_input("Ollama Base URL", value=env_config.get("OLLAMA_API_BASE_URL", "http://host.docker.internal:11434"))
                    ollama_model = st.text_input("Ollama Model", value=env_config.get("OLLAMA_API_MODEL", "deepseek-r1:latest"))
            
            # 第六部分：系统详细配置（多配置项，折叠显示）
            with st.expander("🏠 系统详细配置", expanded=False):
                col3, col4 = st.columns(2)
                
                with col3:
                    log_level = st.selectbox("日志级别", 
                                           ["DEBUG", "INFO", "WARNING", "ERROR"],
                                           index=["DEBUG", "INFO", "WARNING", "ERROR"].index(env_config.get("LOG_LEVEL", "DEBUG")))
                    queue_driver = st.selectbox("队列驱动", 
                                              ["async", "rq"],
                                              index=0 if env_config.get("QUEUE_DRIVER", "async") == "async" else 1)
                    worker_queue = st.text_input("工作队列名称", value=env_config.get("WORKER_QUEUE", "git_test_com"))
                    log_file = st.text_input("日志文件路径", value=env_config.get("LOG_FILE", "log/app.log"))
                
                with col4:
                    supported_extensions = st.text_input("支持的文件扩展名", 
                                                       value=env_config.get("SUPPORTED_EXTENSIONS", ".py,.js,.java,.cpp,.c,.h"))
                    log_max_bytes = st.number_input("日志文件最大字节数", 
                                                  min_value=1024, max_value=104857600, 
                                                  value=int(env_config.get("LOG_MAX_BYTES", "10485760") or "10485760"))
                    log_backup_count = st.number_input("日志备份文件数量", 
                                                     min_value=1, max_value=10, 
                                                     value=int(env_config.get("LOG_BACKUP_COUNT", "3") or "3"))
                    report_cron = st.text_input("工作日报发送时间(Cron)", 
                                              value=env_config.get("REPORT_CRONTAB_EXPRESSION", "0 18 * * 1-5"))
                
                # Redis配置（仅在队列驱动为rq时显示）
                if queue_driver == "rq":
                    st.markdown("**Redis配置**")
                    col_redis1, col_redis2 = st.columns(2)
                    
                    with col_redis1:
                        redis_host = st.text_input("Redis主机", value=env_config.get("REDIS_HOST", "127.0.0.1"))
                    
                    with col_redis2:
                        redis_port = st.number_input("Redis端口", 
                                                   min_value=1, max_value=65535, 
                                                   value=int(env_config.get("REDIS_PORT", "6379") or "6379"))
                else:
                    redis_host = env_config.get("REDIS_HOST", "127.0.0.1")
                    redis_port = int(env_config.get("REDIS_PORT", "6379") or "6379")
            
            # 第七部分：平台详细配置（多配置项，折叠显示）
            with st.expander("🔗 平台详细配置", expanded=False):
                # GitLab配置
                st.markdown("**GitLab配置**")
                col5, col6 = st.columns(2)
                
                with col5:
                    gitlab_url = st.text_input("GitLab URL (可选)", value=env_config.get("GITLAB_URL", ""))
                    gitlab_token = st.text_input("GitLab Access Token (可选)", value=env_config.get("GITLAB_ACCESS_TOKEN", ""), type="password")
                
                with col6:
                    push_review_enabled = st.checkbox("启用Push审查功能", value=env_config.get("PUSH_REVIEW_ENABLED", "1") == "1")
                    merge_protected_only = st.checkbox("仅审查受保护分支", value=env_config.get("MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED", "0") == "1")
                
                # GitHub配置
                st.markdown("**GitHub配置**")
                github_token = st.text_input("GitHub Access Token (可选)", value=env_config.get("GITHUB_ACCESS_TOKEN", ""), type="password")
                
                # SVN配置
                st.markdown("**SVN配置**")
                col7, col8 = st.columns(2)
                
                with col7:
                    svn_check_enabled = st.checkbox("启用SVN代码审查", value=env_config.get("SVN_CHECK_ENABLED", "0") == "1")
                    svn_check_cron = st.text_input("SVN检查时间(Cron)", value=env_config.get("SVN_CHECK_CRONTAB", "*/30 * * * *"))
                
                with col8:
                    svn_check_limit = st.number_input("每次检查最大提交数", 
                                                    min_value=1, max_value=1000, 
                                                    value=int(env_config.get("SVN_CHECK_LIMIT", "100") or "100"))
                    svn_review_enabled = st.checkbox("启用SVN AI审查", value=env_config.get("SVN_REVIEW_ENABLED", "1") == "1")
                  # SVN仓库配置
                st.markdown("**SVN仓库配置**")
                svn_repositories = st.text_area("SVN仓库配置(JSON格式)", 
                                               value=env_config.get("SVN_REPOSITORIES", '[{"name":"example_project","remote_url":"https://example.com/svn/repo/trunk","local_path":"data/svn/project","username":"","password":"","check_hours":1}]'),
                                               height=120,
                                               help="支持多行输入，保存时会自动清理格式。JSON数组格式，包含name、remote_url、local_path、username、password、check_hours字段")
            
            # 第八部分：消息推送配置（多配置项，折叠显示）
            with st.expander("🔔 消息推送配置", expanded=False):
                col9, col10, col11 = st.columns(3)
                
                with col9:
                    st.markdown("**钉钉通知**")
                    dingtalk_enabled = st.checkbox("启用钉钉通知", value=env_config.get("DINGTALK_ENABLED", "0") == "1")
                    dingtalk_webhook = st.text_input("钉钉Webhook URL", value=env_config.get("DINGTALK_WEBHOOK_URL", ""), type="password")
                
                with col10:
                    st.markdown("**企业微信通知**")
                    wecom_enabled = st.checkbox("启用企业微信通知", value=env_config.get("WECOM_ENABLED", "0") == "1")
                    wecom_webhook = st.text_input("企业微信Webhook URL", value=env_config.get("WECOM_WEBHOOK_URL", ""), type="password")
                
                with col11:
                    st.markdown("**飞书通知**")
                    feishu_enabled = st.checkbox("启用飞书通知", value=env_config.get("FEISHU_ENABLED", "0") == "1")
                    feishu_webhook = st.text_input("飞书Webhook URL", value=env_config.get("FEISHU_WEBHOOK_URL", ""), type="password")
                
                # 额外Webhook配置
                st.markdown("**额外Webhook配置**")
                col_webhook1, col_webhook2 = st.columns(2)
                
                with col_webhook1:
                    extra_webhook_enabled = st.checkbox("启用额外Webhook", value=env_config.get("EXTRA_WEBHOOK_ENABLED", "0") == "1")
                
                with col_webhook2:
                    extra_webhook_url = st.text_input("额外Webhook URL", value=env_config.get("EXTRA_WEBHOOK_URL", ""), type="password")            # 保存按钮
            if st.form_submit_button("💾 保存系统配置", use_container_width=True, type="primary"):
                # 处理SVN仓库配置JSON格式 - 智能清理和验证
                try:
                    # 第一步：基础清理 - 移除首尾空白
                    svn_repositories_cleaned = svn_repositories.strip()
                    
                    # 第二步：智能处理换行和空格
                    if svn_repositories_cleaned:
                        # 保留JSON结构的换行，但清理多余的空白
                        import re
                        # 移除行首行尾空白，但保留结构化的空格
                        lines = [line.strip() for line in svn_repositories_cleaned.split('\n') if line.strip()]
                        svn_repositories_cleaned = ''.join(lines)
                        
                        # 进一步清理：移除不必要的空格（但保留字符串内的空格）
                        # 这个正则表达式会移除JSON结构符号周围的多余空格
                        svn_repositories_cleaned = re.sub(r'\s*([{}[\]:,])\s*', r'\1', svn_repositories_cleaned)
                        
                    # 第三步：验证JSON格式
                    if svn_repositories_cleaned:
                        parsed_json = json.loads(svn_repositories_cleaned)
                        # 重新格式化为紧凑的JSON（可选，确保一致性）
                        svn_repositories_final = json.dumps(parsed_json, separators=(',', ':'), ensure_ascii=False)
                    else:
                        svn_repositories_final = ""
                        
                except json.JSONDecodeError as e:
                    st.error(f"❌ SVN仓库配置JSON格式错误: {e}")
                    st.error("💡 提示：请检查JSON格式，确保括号、引号、逗号等符号正确匹配")
                    st.stop()
                except Exception as e:
                    st.error(f"❌ SVN仓库配置处理失败: {e}")
                    st.stop()
                
                new_config = {
                    # AI模型配置
                    "LLM_PROVIDER": llm_provider,
                    "REVIEW_STYLE": review_style,
                    "REVIEW_MAX_TOKENS": str(review_max_tokens),
                    "SUPPORTED_EXTENSIONS": supported_extensions,
                    
                    # 平台开关配置
                    "SVN_CHECK_ENABLED": "1" if svn_enabled else "0",
                    "GITLAB_ENABLED": "1" if gitlab_enabled else "0",
                    "GITHUB_ENABLED": "1" if github_enabled else "0",
                    
                    # 版本追踪配置
                    "VERSION_TRACKING_ENABLED": "1" if version_tracking_enabled else "0",
                    "REUSE_PREVIOUS_REVIEW_RESULT": "1" if reuse_previous_review else "0",
                    "VERSION_TRACKING_RETENTION_DAYS": str(retention_days),
                    
                    # 系统配置
                    "SERVER_PORT": server_port,
                    "TZ": timezone,
                    "LOG_LEVEL": log_level,
                    "QUEUE_DRIVER": queue_driver,
                    "WORKER_QUEUE": worker_queue,
                    "LOG_FILE": log_file,
                    "LOG_MAX_BYTES": str(log_max_bytes),
                    "LOG_BACKUP_COUNT": str(log_backup_count),
                    
                    # 报告配置
                    "REPORT_CRONTAB_EXPRESSION": report_cron,
                    
                    # GitLab配置
                    "GITLAB_URL": gitlab_url,
                    "GITLAB_ACCESS_TOKEN": gitlab_token,
                    "PUSH_REVIEW_ENABLED": "1" if push_review_enabled else "0",
                    "MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED": "1" if merge_protected_only else "0",
                    
                    # GitHub配置
                    "GITHUB_ACCESS_TOKEN": github_token,
                      # SVN配置
                    "SVN_CHECK_ENABLED": "1" if svn_check_enabled else "0",
                    "SVN_CHECK_CRONTAB": svn_check_cron,
                    "SVN_CHECK_LIMIT": str(svn_check_limit),
                    "SVN_REVIEW_ENABLED": "1" if svn_review_enabled else "0",
                    "SVN_REPOSITORIES": svn_repositories_final,
                    
                    # 消息推送配置
                    "DINGTALK_ENABLED": "1" if dingtalk_enabled else "0",
                    "DINGTALK_WEBHOOK_URL": dingtalk_webhook,
                    "WECOM_ENABLED": "1" if wecom_enabled else "0",
                    "WECOM_WEBHOOK_URL": wecom_webhook,
                    "FEISHU_ENABLED": "1" if feishu_enabled else "0",
                    "FEISHU_WEBHOOK_URL": feishu_webhook,
                    
                    # 额外Webhook配置
                    "EXTRA_WEBHOOK_ENABLED": "1" if extra_webhook_enabled else "0",
                    "EXTRA_WEBHOOK_URL": extra_webhook_url,
                      # Dashboard配置
                    "DASHBOARD_USER": dashboard_user,
                    "DASHBOARD_PASSWORD": dashboard_password
                }
                
                # Redis配置（如果使用rq队列）
                if queue_driver == "rq":
                    new_config.update({
                        "REDIS_HOST": redis_host,
                        "REDIS_PORT": str(redis_port)
                    })
                else:
                    # 即使不使用rq，也保留Redis配置
                    new_config.update({
                        "REDIS_HOST": redis_host,
                        "REDIS_PORT": str(redis_port)
                    })
                  # 保存所有AI模型配置
                new_config.update({
                    # DeepSeek配置
                    "DEEPSEEK_API_KEY": deepseek_key,
                    "DEEPSEEK_API_BASE_URL": deepseek_base,
                    "DEEPSEEK_API_MODEL": deepseek_model,
                    
                    # OpenAI配置
                    "OPENAI_API_KEY": openai_key,
                    "OPENAI_API_BASE_URL": openai_base,
                    "OPENAI_API_MODEL": openai_model,
                    
                    # 智谱AI配置
                    "ZHIPUAI_API_KEY": zhipuai_key,
                    "ZHIPUAI_API_MODEL": zhipuai_model,
                      # Qwen配置
                    "QWEN_API_KEY": qwen_key,
                    "QWEN_API_BASE_URL": qwen_base,
                    "QWEN_API_MODEL": qwen_model,
                    
                    # Ollama配置
                    "OLLAMA_API_BASE_URL": ollama_base,
                    "OLLAMA_API_MODEL": ollama_model                })
                
                try:
                    if config_manager.save_env_config(new_config):
                        st.success("✅ 系统配置已成功保存！")
                        st.info("💡 配置更改需要重启应用程序才能生效。")
                        # 建议重新加载环境变量
                        load_dotenv("conf/.env", override=True)
                        
                        # 保存成功后自动刷新页面
                        st.info("🔄 页面即将自动刷新...")
                        import time
                        time.sleep(1)  # 让用户看到成功消息
                        st.rerun()
                    else:
                        st.error("❌ 保存配置失败，请检查文件权限。")
                except Exception as e:
                    st.error(f"❌ 保存配置失败: {e}")
    
    with tab2:
        st.markdown("### 📋 配置总览")
        st.markdown("查看系统的所有配置项及其当前状态。")
        
        try:
            current_config = config_manager.get_env_config()
            
            if current_config:
                # 按类别分组显示
                categories = {
                    "🤖 AI模型配置": ["LLM_PROVIDER", "DEEPSEEK_API_KEY", "DEEPSEEK_API_BASE_URL", "DEEPSEEK_API_MODEL", 
                                   "OPENAI_API_KEY", "OPENAI_API_BASE_URL", "OPENAI_API_MODEL",
                                   "ZHIPUAI_API_KEY", "ZHIPUAI_API_MODEL", 
                                   "QWEN_API_KEY", "QWEN_API_BASE_URL", "QWEN_API_MODEL",
                                   "OLLAMA_API_BASE_URL", "OLLAMA_API_MODEL",
                                   "REVIEW_STYLE", "REVIEW_MAX_TOKENS", "SUPPORTED_EXTENSIONS"],
                    "🔀 平台开关": ["SVN_CHECK_ENABLED", "GITLAB_ENABLED", "GITHUB_ENABLED"],
                    "📋 版本追踪配置": ["VERSION_TRACKING_ENABLED", "REUSE_PREVIOUS_REVIEW_RESULT", "VERSION_TRACKING_RETENTION_DAYS"],
                    "🏠 系统配置": ["SERVER_PORT", "TZ", "LOG_LEVEL", "LOG_FILE", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT", "QUEUE_DRIVER", "WORKER_QUEUE"],
                    "⚡ Redis配置": ["REDIS_HOST", "REDIS_PORT"],
                    "📊 报告配置": ["REPORT_CRONTAB_EXPRESSION"],
                    "🔗 GitLab配置": ["GITLAB_URL", "GITLAB_ACCESS_TOKEN", "PUSH_REVIEW_ENABLED", "MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED"],
                    "🐙 GitHub配置": ["GITHUB_ACCESS_TOKEN"],
                    "📂 SVN配置": ["SVN_CHECK_CRONTAB", "SVN_CHECK_LIMIT", "SVN_REVIEW_ENABLED", "SVN_REPOSITORIES"],
                    "🔔 消息推送": ["DINGTALK_ENABLED", "DINGTALK_WEBHOOK_URL", "WECOM_ENABLED", "WECOM_WEBHOOK_URL", "FEISHU_ENABLED", "FEISHU_WEBHOOK_URL"],
                    "🔗 额外Webhook": ["EXTRA_WEBHOOK_ENABLED", "EXTRA_WEBHOOK_URL"],
                    "👤 Dashboard": ["DASHBOARD_USER", "DASHBOARD_PASSWORD"]
                }
                
                for category, keys in categories.items():
                    st.markdown(f"#### {category}")
                    
                    category_data = []
                    for key in keys:
                        if key in current_config:
                            value = current_config[key]
                            # 隐藏敏感信息
                            if any(sensitive in key.upper() for sensitive in ["PASSWORD", "TOKEN", "KEY", "SECRET", "WEBHOOK"]):
                                if value:
                                    display_value = "••••••••" + value[-4:] if len(value) > 4 else "••••••••"
                                else:
                                    display_value = "未设置"
                            else:
                                display_value = value if value else "未设置"
                            
                            category_data.append({
                                "配置项": key,
                                "当前值": display_value,
                                "状态": "✅ 已配置" if value else "⚠️ 未配置"
                            })
                    
                    if category_data:
                        df = pd.DataFrame(category_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("该类别暂无配置项")
                    
                    st.markdown("---")
                
                # 配置统计
                total_items = len(current_config)
                configured_items = len([v for v in current_config.values() if v])
                st.markdown("#### 📊 配置统计")
                
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("总配置项", total_items)
                with col_stat2:                    st.metric("已配置项", configured_items)
                with col_stat3:
                    completion_rate = (configured_items / total_items * 100) if total_items > 0 else 0
                    st.metric("配置完成度", f"{completion_rate:.1f}%")
                    
            else:
                st.warning("⚠️ 无法读取环境变量配置")
                
        except Exception as e:
            st.error(f"❌ 读取配置失败: {e}")
    
    with tab3:
        st.markdown("### � 配置模板管理")
        st.markdown("🚀 **快速部署配置模板**，根据不同环境选择最佳配置组合。")
        
        col_template1, col_template2 = st.columns(2)
        
        with col_template1:
            st.markdown("#### � 环境模板")
            
            templates = {
                "🔧 开发环境": {
                    "LLM_PROVIDER": "deepseek",
                    "LOG_LEVEL": "DEBUG",
                    "SVN_CHECK_ENABLED": "1",
                    "GITLAB_ENABLED": "1",
                    "GITHUB_ENABLED": "1",
                    "DINGTALK_ENABLED": "0",
                    "WECOM_ENABLED": "0",
                    "FEISHU_ENABLED": "0"
                },
                "🚀 生产环境": {
                    "LLM_PROVIDER": "openai",
                    "LOG_LEVEL": "INFO",
                    "SVN_CHECK_ENABLED": "1",
                    "GITLAB_ENABLED": "1",
                    "GITHUB_ENABLED": "1",
                    "DINGTALK_ENABLED": "1",
                    "WECOM_ENABLED": "1",
                    "FEISHU_ENABLED": "1"
                },
                "🧪 测试环境": {
                    "LLM_PROVIDER": "ollama",
                    "LOG_LEVEL": "DEBUG",
                    "SVN_CHECK_ENABLED": "1",
                    "GITLAB_ENABLED": "1",
                    "GITHUB_ENABLED": "0",
                    "DINGTALK_ENABLED": "0",
                    "WECOM_ENABLED": "0",
                    "FEISHU_ENABLED": "0"
                }
            }
            
            selected_template = st.selectbox("选择模板", list(templates.keys()))
            
            if selected_template:
                st.markdown(f"**{selected_template}配置预览:**")
                template_config = templates[selected_template]
                
                for key, value in template_config.items():
                    st.text(f"{key}: {value}")
                
                if st.button(f"应用{selected_template}模板", key="apply_template"):
                    try:
                        current_config = config_manager.get_env_config()
                        current_config.update(template_config)
                        
                        if config_manager.save_env_config(current_config):
                            st.success(f"✅ {selected_template}模板已应用！")
                            st.info("💡 请重启应用程序使配置生效。")
                        else:
                            st.error("❌ 应用模板失败")
                    except Exception as e:
                        st.error(f"❌ 应用模板失败: {e}")
        
        with col_template2:
            st.markdown("#### 🔄 配置操作")
            
            # 重置配置
            if st.button("🔄 重置为默认配置", key="reset_config"):
                try:
                    if config_manager.reset_env_config():
                        st.success("✅ 配置已重置为默认值！")
                        st.info("💡 请重启应用程序使配置生效。")
                    else:
                        st.error("❌ 重置配置失败")
                except Exception as e:
                    st.error(f"❌ 重置配置失败: {e}")
            
            st.markdown("---")
            
            # 导出配置
            if st.button("📥 导出当前配置", key="export_config"):
                try:
                    current_config = config_manager.get_env_config()
                    if current_config:
                        # 创建导出内容
                        export_content = "# AI代码审查系统配置文件\n"
                        export_content += f"# 导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        

                        for key, value in current_config.items():
                            export_content += f"{key}={value}\n"
                        
                        st.download_button(
                            label="下载配置文件",
                            data=export_content,
                            file_name=f"env_config_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.env",
                            mime="text/plain"
                        )
                    else:
                        st.error("❌ 无法读取当前配置")
                except Exception as e:
                    st.error(f"❌ 导出配置失败: {e}")

# 持久化登录状态管理
def get_session_file_path():
    """获取session文件路径"""
    # 使用简单的固定文件名
    return os.path.join(tempfile.gettempdir(), "streamlit_ai_codereview_session.json")

def save_login_state(username):
    """保存登录状态到文件"""
    try:
        session_data = {
            "username": username,
            "timestamp": datetime.datetime.now().isoformat(),
            "authenticated": True
        }
        with open(get_session_file_path(), 'w', encoding='utf-8') as f:
            json.dump(session_data, f)
        return True
    except Exception as e:
        st.error(f"保存登录状态失败: {e}")
        return False

def load_login_state():
    """从文件加载登录状态"""
    try:
        session_file = get_session_file_path()
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 检查session是否过期（24小时）
            timestamp = datetime.datetime.fromisoformat(session_data['timestamp'])
            if datetime.datetime.now() - timestamp < datetime.timedelta(hours=24):
                return session_data
        return None
    except Exception as e:
        # 如果读取失败，删除无效文件
        try:
            if os.path.exists(get_session_file_path()):
                os.remove(get_session_file_path())
        except:
            pass
        return None

def clear_login_state():
    """清除登录状态文件"""
    try:
        session_file = get_session_file_path()
        if os.path.exists(session_file):
            os.remove(session_file)
        return True
    except Exception as e:
        st.error(f"清除登录状态失败: {e}")
        return False

# 初始化session state - 增强持久化处理
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# 增强session持久化，防止页面刷新后丢失登录状态
if "username" not in st.session_state:
    st.session_state["username"] = None

# 添加一个session计数器来追踪session状态
if "session_counter" not in st.session_state:
    st.session_state["session_counter"] = 0
st.session_state["session_counter"] += 1

# 尝试从持久化文件恢复登录状态（页面刷新后保持登录）
if not st.session_state["authenticated"]:
    # 先尝试从URL参数恢复
    query_params = st.query_params
      # 调试信息（可以注释掉）
    # st.write(f"Debug: Query params: {dict(query_params)}")
    # st.write(f"Debug: Session counter: {st.session_state['session_counter']}")
    # st.write(f"Debug: Authenticated: {st.session_state['authenticated']}")
    # st.write(f"Debug: Username: {st.session_state.get('username', 'None')}")
    
    restored = False
    
    # 方法1：从URL参数恢复
    if "auto_login" in query_params and query_params["auto_login"] == "true" and "user" in query_params:
        username = query_params["user"]
        if username:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            # st.write(f"Debug: Restored login from URL for user: {username}")
            restored = True
    
    # 方法2：从持久化文件恢复
    if not restored:
        saved_state = load_login_state()
        if saved_state and saved_state.get('authenticated'):
            username = saved_state.get('username')
            if username:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                # st.write(f"Debug: Restored login from file for user: {username}")
                restored = True
    
    # 如果成功恢复，刷新页面以更新UI
    if restored:
        st.rerun()

# 主程序逻辑
if not st.session_state["authenticated"]:
    login_page()
else:
    main_dashboard()
