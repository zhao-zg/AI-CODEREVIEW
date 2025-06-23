#!/usr/bin/env python3
"""
多类型代码审查UI - 支持SVN、GitLab、GitHub
"""

import datetime
import math
import os
import sys

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib
from biz.service.review_service import ReviewService

# 导入配置文件
try:
    from conf.dashboard_config import *
except ImportError:
    # 如果配置文件不存在，使用默认值
    DASHBOARD_TITLE = "AI 代码审查仪表板"
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
        <h1>🤖 AI 代码审查仪表板</h1>
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
                st.success("✅ 登录成功！")
                st.rerun()
            else:
                st.error("❌ 用户名或密码错误！")

def main_dashboard():
    """主仪表板"""
    # 页面标题
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                border-radius: 10px; margin-bottom: 2rem; color: white;">
        <h1>🤖 AI 代码审查仪表板</h1>
        <p>多平台代码质量监控与分析系统</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        if "username" in st.session_state:
            st.success(f"👤 欢迎，{st.session_state['username']}！")
        
        st.markdown("---")
        st.markdown("### 🛠️ 功能菜单")
        
        if st.button("🔄 刷新数据", use_container_width=True, key="refresh_all"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        if st.button("🚪 注销", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state.pop("username", None)
            st.rerun()
    
    # 审查类型选择
    st.markdown("### 📋 审查数据分析")
    
    # 获取审查类型统计
    review_stats = ReviewService().get_review_type_stats()
    
    # 构建可用类型列表
    available_types = []
    type_labels = {}
    
    # 检查各种类型的数据
    if review_stats.get('mr_count', 0) > 0:
        available_types.append('mr')
        type_labels['mr'] = f"🔀 GitLab MR ({review_stats['mr_count']} 条)"
    
    if review_stats.get('push_count', 0) > 0:
        available_types.append('push')
        type_labels['push'] = f"📤 GitLab Push ({review_stats['push_count']} 条)"
    
    if review_stats.get('svn_count', 0) > 0:
        available_types.append('svn')
        type_labels['svn'] = f"📂 SVN 提交 ({review_stats['svn_count']} 条)"
    
    if review_stats.get('github_count', 0) > 0:
        available_types.append('github')
        type_labels['github'] = f"🐙 GitHub ({review_stats['github_count']} 条)"
    
    if review_stats.get('gitlab_count', 0) > 0:
        available_types.append('gitlab')
        type_labels['gitlab'] = f"🦊 GitLab 通用 ({review_stats['gitlab_count']} 条)"
    
    # 如果没有数据，显示所有类型选项
    if not available_types:
        available_types = ['svn', 'mr', 'push', 'github', 'gitlab']
        type_labels = {
            'svn': '📂 SVN 提交 (暂无数据)',
            'mr': '🔀 GitLab MR (暂无数据)',
            'push': '📤 GitLab Push (暂无数据)',
            'github': '🐙 GitHub (暂无数据)',
            'gitlab': '🦊 GitLab 通用 (暂无数据)'
        }
    
    # 类型选择
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_review_type = st.selectbox(
            "选择审查数据类型",
            options=available_types,
            format_func=lambda x: type_labels.get(x, x),
            key="main_review_type_selector"
        )
    
    with col2:
        if st.button("🔄 刷新统计", use_container_width=True, key="refresh_stats"):
            st.cache_data.clear()
            st.rerun()
    
    # 显示对应的数据
    if selected_review_type in ['mr', 'push']:
        # 传统MR/Push数据
        display_legacy_data(selected_review_type)
    else:
        # 版本跟踪数据（SVN、GitHub、GitLab通用）
        with st.expander("🔍 高级筛选条件", expanded=False):
            filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
            
            with filter_col1:
                authors = st.multiselect(
                    "👤 开发者筛选", 
                    options=get_available_authors([selected_review_type]), 
                    key="main_author_filter"
                )
            
            with filter_col2:
                projects = st.multiselect(
                    "📦 项目筛选", 
                    options=get_available_projects([selected_review_type]), 
                    key="main_project_filter"
                )
            
            with filter_col3:
                date_range = st.date_input(
                    "📅 时间范围", 
                    value=[],
                    max_value=datetime.date.today(),
                    key="main_date_filter"
                )
            
            with filter_col4:
                score_range = st.slider(
                    "📊 分数范围", 
                    0, 100, (0, 100), 
                    key="main_score_filter"
                )
        
        # 显示数据
        display_version_tracking_data(
            selected_review_type, 
            authors if authors else None, 
            projects if projects else None, 
            date_range if date_range else None, 
            score_range
        )

# 初始化session state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# 主程序逻辑
if not st.session_state["authenticated"]:
    login_page()
else:
    main_dashboard()
