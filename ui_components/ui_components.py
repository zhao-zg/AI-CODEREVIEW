# -*- coding: utf-8 -*-
"""UI组件模块 - 提供通用的UI组件和界面元素"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class UITheme:
    """UI主题配置"""
    
    # 颜色配置
    COLORS = {
        'primary': '#FF6B6B',
        'secondary': '#4ECDC4', 
        'success': '#00B894',
        'warning': '#FDCB6E',
        'error': '#E17055',
        'info': '#74B9FF'
    }
    
    # 图标配置
    ICONS = {
        'mr': '🔄',
        'push': '📤',
        'svn': '📁',
        'author': '👤',
        'project': '📁',
        'score': '⭐', 
        'time': '🕒',
        'chart': '📊',
        'export': '📥',
        'search': '🔍',
        'filter': '🔽',
        'detail': '👁️'
    }


class UIComponents:
    """UI组件类"""
    
    def __init__(self):
        self.theme = UITheme()
    
    def show_page_header(self, title: str, subtitle: str = None, icon: str = None):
        """显示页面头部"""
        if icon:
            title = f"{icon} {title}"
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(90deg, {self.theme.COLORS['primary']} 0%, {self.theme.COLORS['secondary']} 100%);
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
        ">
            <h1 style="margin: 0; font-size: 2.5rem; font-weight: 600;">{title}</h1>
            {f'<p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;">{subtitle}</p>' if subtitle else ''}
        </div>
        """, unsafe_allow_html=True)
    
    def show_query_summary(self, review_type: str, authors: Optional[List[str]] = None, 
                          projects: Optional[List[str]] = None, 
                          date_range: Optional[Tuple] = None, 
                          score_range: Tuple[int, int] = (0, 100)):
        """显示查询摘要 - 优化版本"""
        
        # 构建查询信息
        query_items = []
        
        # 数据源信息
        source_icon = self.theme.ICONS.get(review_type, '📊')
        query_items.append(f"{source_icon} **{review_type.upper()}数据**")
        
        # 筛选条件
        if authors:
            query_items.append(f"{self.theme.ICONS['author']} 作者: {len(authors)}个")
        if projects:
            query_items.append(f"{self.theme.ICONS['project']} 项目: {len(projects)}个")
        if date_range:
            start_date = date_range[0].strftime('%Y-%m-%d') if date_range[0] else '开始'
            end_date = date_range[1].strftime('%Y-%m-%d') if date_range[1] else '结束'
            query_items.append(f"{self.theme.ICONS['time']} 时间: {start_date} ~ {end_date}")
        if score_range != (0, 100):
            query_items.append(f"{self.theme.ICONS['score']} 评分: {score_range[0]}-{score_range[1]}")
        
        # 显示查询摘要
        query_text = " | ".join(query_items)
        
        st.markdown(f"""
        <div style="
            background-color: #f8f9fa;
            border-left: 4px solid {self.theme.COLORS['info']};
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 5px;
        ">
            <div style="font-size: 1rem; color: #495057;">
                {query_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def show_no_data_help(self, review_type: str):
        """显示无数据帮助信息 - 优化版本"""
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            margin: 2rem 0;
        ">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🔍</div>
            <h2 style="margin: 0 0 1rem 0;">暂无 {review_type.upper()} 数据</h2>
            <p style="font-size: 1.1rem; margin-bottom: 2rem; opacity: 0.9;">
                当前筛选条件下没有找到匹配的数据记录
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 帮助信息
        with st.expander("💡 可能的原因和解决方案", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🔍 可能的原因:**
                - 数据库中没有对应类型的数据
                - 筛选条件过于严格
                - 时间范围设置不当
                - 数据服务连接异常
                """)
            
            with col2:
                st.markdown("""
                **💡 建议操作:**
                - 检查数据库连接状态
                - 放宽筛选条件范围
                - 调整时间范围设置
                - 查看系统日志信息
                """)
    
    def create_filter_panel(self, df: pd.DataFrame) -> Dict[str, Any]:
        """创建筛选面板"""
        st.markdown("### 🔽 筛选条件")
        
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        filters = {}
        
        with filter_col1:
            # 作者筛选
            if 'author' in df.columns:
                unique_authors = sorted(df['author'].dropna().unique())
                if unique_authors:
                    filters['authors'] = st.multiselect(
                        f"{self.theme.ICONS['author']} 选择作者",
                        options=unique_authors,
                        default=[],
                        help="选择要筛选的作者，留空显示所有作者"
                    )
        
        with filter_col2:
            # 项目筛选
            if 'project_name' in df.columns:
                unique_projects = sorted(df['project_name'].dropna().unique())
                if unique_projects:
                    filters['projects'] = st.multiselect(
                        f"{self.theme.ICONS['project']} 选择项目",
                        options=unique_projects,
                        default=[],
                        help="选择要筛选的项目，留空显示所有项目"
                    )
        
        with filter_col3:
            # 评分筛选
            if 'score' in df.columns and df['score'].notna().any():
                min_score = float(df['score'].min())
                max_score = float(df['score'].max())
                filters['score_range'] = st.slider(
                    f"{self.theme.ICONS['score']} 评分范围",
                    min_value=min_score,
                    max_value=max_score,
                    value=(min_score, max_score),
                    step=0.1,
                    help="设置评分筛选范围"
                )
            else:
                filters['score_range'] = (0, 100)
        
        return filters
    
    def create_data_table_controls(self) -> Dict[str, Any]:
        """创建数据表控制面板"""
        
        control_col1, control_col2, control_col3, control_col4 = st.columns(4)
        controls = {}
        
        with control_col1:
            controls['search_term'] = st.text_input(
                f"{self.theme.ICONS['search']} 搜索",
                placeholder="输入关键词搜索...",
                help="在所有文本字段中搜索关键词"
            )
        
        with control_col2:
            controls['page_size'] = st.selectbox(
                "📄 每页显示",
                options=[20, 50, 100, 200],
                index=1,
                help="设置每页显示的记录数"
            )
        
        with control_col3:
            controls['sort_by'] = st.selectbox(
                "📊 排序方式",
                options=["时间倒序", "时间正序", "评分倒序", "评分正序", "作者", "项目"],
                index=0,
                help="选择数据排序方式"
            )
        
        with control_col4:
            controls['export_format'] = st.selectbox(
                f"{self.theme.ICONS['export']} 导出格式",
                options=["CSV", "Excel", "JSON"],
                help="选择数据导出格式"
            )
        
        return controls
    
    def show_data_card(self, row: pd.Series, index: int, review_type: str) -> str:
        """显示数据卡片 - 可点击展开详情"""
        
        # 为每个卡片创建唯一的展开状态键
        expand_key = f"expand_card_{index}_{review_type}"
        
        # 初始化 session state
        if expand_key not in st.session_state:
            st.session_state[expand_key] = False
        
        # 格式化评分显示
        score_val = row.get('score', 0)
        score_display = f"{int(score_val)}分" if score_val and score_val > 0 else "N/A"
        
        # 创建可点击的卡片
        with st.container():
            # 卡片内容
            card_html = f"""
            <div style="
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 10px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: box-shadow 0.3s ease;
                cursor: pointer;
            ">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #495057; margin-bottom: 0.5rem;">
                            #{index} | {self.theme.ICONS.get(review_type, '📊')} {review_type.upper()}
                        </div>
                        <div style="color: #6c757d; font-size: 0.9rem;">
                            <span style="margin-right: 1rem;">
                                {self.theme.ICONS['author']} {row.get('author', 'N/A')}
                            </span>
                            <span style="margin-right: 1rem;">
                                {self.theme.ICONS['project']} {row.get('project', row.get('project_name', 'N/A'))}
                            </span>
                            <span style="margin-right: 1rem;">
                                {self.theme.ICONS['score']} {score_display}
                            </span>
                            <span>
                                {self.theme.ICONS['time']} {self._format_datetime(row.get('timestamp', row.get('datetime', row.get('reviewed_at', 'N/A'))))}
                            </span>
                        </div>
                        <div style="margin-top: 0.5rem; color: #495057; font-size: 0.85rem;">
                            <strong>提交:</strong> {str(row.get('commit_messages', row.get('commit_message', 'N/A')))[:80]}{'...' if len(str(row.get('commit_messages', row.get('commit_message', '')))) > 80 else ''}
                        </div>
                    </div>
                    <div style="color: #6c757d; font-size: 0.8rem;">
                        {'📖 点击收起' if st.session_state[expand_key] else '👁️ 点击展开'}
                    </div>
                </div>
            </div>
            """
            
            st.markdown(card_html, unsafe_allow_html=True)
            
            # 展开/收起按钮
            current_state = st.session_state[expand_key]
            button_text = "📖 收起详情" if current_state else "�️ 展开详情"
            
            if st.button(button_text, key=f"btn_{expand_key}", use_container_width=True):
                st.session_state[expand_key] = not st.session_state[expand_key]
                st.rerun()
            
            return "expanded" if st.session_state[expand_key] else "collapsed"
    
    def show_detail_modal(self, row: pd.Series, review_type: str):
        """显示详情模态框 - 优化版本"""
        
        # 基本信息
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            st.markdown("#### 📋 基本信息")
            score_val = row.get('score', 0)
            score_display = f"{int(score_val)}分" if score_val and score_val > 0 else "N/A"
            info_data = {
                "作者": row.get('author', 'N/A'),
                "项目": row.get('project', row.get('project_name', 'N/A')),
                "评分": score_display,
                "类型": review_type.upper(),
                "提交ID": row.get('commit_sha', 'N/A')
            }
            
            for key, value in info_data.items():
                st.write(f"**{key}:** {value}")
        
        with detail_col2:
            st.markdown("#### 🕒 时间信息")
            time_data = {
                "审查时间": self._format_datetime(row.get('timestamp', row.get('reviewed_at', 'N/A'))),
                "提交时间": self._format_datetime(row.get('commit_date', 'N/A')),
                "创建时间": self._format_datetime(row.get('created_at', 'N/A'))
            }
            
            for key, value in time_data.items():
                st.write(f"**{key}:** {value}")
        
        # 提交信息
        if row.get('commit_messages') or row.get('commit_message') or row.get('title'):
            st.markdown("#### 💬 提交信息")
            message = row.get('commit_messages', row.get('commit_message', row.get('title', 'N/A')))
            # 使用唯一的key避免ID冲突
            unique_id = row.get('commit_sha') or row.get('version_hash') or row.get('id') or str(row.get('created_at', ''))
            st.text_area("提交消息", value=str(message), height=100, disabled=True, key=f"commit_msg_{unique_id}")
        
        # 审查结果
        if row.get('review_result'):
            st.markdown("#### 📝 审查结果")
            review_result = str(row.get('review_result', ''))
            # 使用唯一的key避免ID冲突
            unique_id = row.get('commit_sha') or row.get('version_hash') or row.get('id') or str(row.get('created_at', ''))
            if len(review_result) > 1000:
                # 长文本使用可展开组件
                with st.expander("点击查看完整审查结果", expanded=False):
                    st.markdown(review_result)
            else:
                st.text_area("审查详情", value=review_result, height=200, disabled=True, key=f"review_result_{unique_id}")
        
        # 重新评审按钮（仅管理员可见）
        from ui_components.auth import check_authentication
        is_admin = check_authentication()
        unique_id = row.get('commit_sha') or row.get('version_hash') or row.get('id') or row.get('created_at')
        if unique_id and is_admin:
            if st.button("🔄 重新AI评审", key=f"retry_review_{unique_id}"):
                import requests
                from biz.utils.default_config import get_env_with_default
                # 使用API_URL配置
                api_url_base = get_env_with_default('API_URL', 'http://localhost:5001')
                api_url = f"{api_url_base}/review/retry"
                payload = {"type": review_type, "id": unique_id}
                try:
                    resp = requests.post(api_url, json=payload, timeout=30)
                    if resp.status_code == 200 and resp.json().get("success"):
                        st.success("已提交重新评审请求，稍后刷新可查看最新结果。")
                    else:
                        st.error(f"重新评审失败: {resp.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")
        
        # 代码变更
        st.markdown("#### 📊 代码变更统计")
        change_col1, change_col2, change_col3 = st.columns(3)
        
        with change_col1:
            additions = row.get('additions', row.get('additions_count', 0))
            st.metric("🟢 新增行数", additions)
        
        with change_col2:
            deletions = row.get('deletions', row.get('deletions_count', 0))
            st.metric("🔴 删除行数", deletions)
        
        with change_col3:
            # 尝试从 file_details 或 file_paths 计算文件数
            files_changed = 0
            if row.get('file_details'):
                try:
                    import json
                    file_details = json.loads(str(row.get('file_details', '{}')))
                    files_changed = file_details.get('summary', {}).get('total_files', 0)
                except:
                    pass
            if files_changed == 0 and row.get('file_paths'):
                try:
                    import json
                    file_paths = json.loads(str(row.get('file_paths', '[]')))
                    files_changed = len(file_paths) if isinstance(file_paths, list) else 0
                except:
                    files_changed = row.get('files_changed', 0)
            
            st.metric("📄 变更文件", files_changed)
        
        # 完整数据
        with st.expander("🔍 查看完整数据", expanded=False):
            st.markdown("#### 📋 所有字段信息")
            
            # 按类别组织字段
            field_categories = {
                "基础信息": ['author', 'project_name', 'title', 'score'],
                "时间信息": ['datetime', 'reviewed_at', 'created_at', 'updated_at'],
                "代码变更": ['additions', 'deletions', 'additions_count', 'deletions_count', 'files_changed'],
                "其他信息": []
            }
            
            # 分配其他字段
            assigned_fields = set()
            for category_fields in field_categories.values():
                assigned_fields.update(category_fields)
            
            for key in row.index:
                if key not in assigned_fields and pd.notna(row[key]):
                    field_categories["其他信息"].append(key)
            
            # 显示各类别字段
            for category, fields in field_categories.items():
                if fields:
                    st.markdown(f"**{category}:**")
                    for field in fields:
                        if field in row.index and pd.notna(row[field]):
                            st.write(f"• **{field}:** {row[field]}")
    
    def _format_datetime(self, dt_value):
        """格式化时间显示为东八区（Asia/Shanghai）"""
        import pandas as pd
        if pd.isna(dt_value) or dt_value == 'N/A':
            return 'N/A'
        try:
            # 1. int/float 视为UTC秒级时间戳
            if isinstance(dt_value, (int, float)):
                dt = pd.to_datetime(dt_value, unit='s', utc=True)
            # 2. str 先转datetime
            elif isinstance(dt_value, str):
                dt = pd.to_datetime(dt_value, utc=True)
            else:
                dt = dt_value
            # 3. 转东八区
            if hasattr(dt, 'tz_convert'):
                dt = dt.tz_convert('Asia/Shanghai')
            elif hasattr(dt, 'astimezone'):
                from zoneinfo import ZoneInfo
                dt = dt.astimezone(ZoneInfo('Asia/Shanghai'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return str(dt_value)
    
    def show_loading_spinner(self, message: str = "正在加载数据..."):
        """显示加载动画"""
        with st.spinner(message):
            return st.empty()
    
    def show_success_message(self, message: str, icon: str = "✅"):
        """显示成功消息"""
        st.success(f"{icon} {message}")
    
    def show_error_message(self, message: str, icon: str = "❌"):
        """显示错误消息"""
        st.error(f"{icon} {message}")
    
    def show_warning_message(self, message: str, icon: str = "⚠️"):
        """显示警告消息"""
        st.warning(f"{icon} {message}")
    
    def show_info_message(self, message: str, icon: str = "ℹ️"):
        """显示信息消息"""
        st.info(f"{icon} {message}")
