"""
UI配置和样式模块
"""

import streamlit as st

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

def setup_page_config():
    """设置Streamlit页面配置"""
    st.set_page_config(
        page_title=DASHBOARD_TITLE,
        page_icon=DASHBOARD_ICON,
        layout=DASHBOARD_LAYOUT,
        initial_sidebar_state="expanded"
    )

def apply_custom_css():
    """应用自定义CSS样式"""
    st.markdown("""
    <style>
    /* 主要布局 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* 卡片样式 */
    .config-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    /* 图表样式 */
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    /* 表格样式 */
    .dataframe {
        border: none !important;
    }
    
    .dataframe th {
        background-color: #f8f9fa !important;
        color: #495057 !important;
        font-weight: 600 !important;
        border: none !important;
    }
    
    .dataframe td {
        border: none !important;
        padding: 0.75rem !important;
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* 按钮样式 */
    .stButton > button {
        border-radius: 5px;
        border: none;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* 选择框样式 */
    .stSelectbox > div > div > div {
        border-radius: 5px;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 5px;
    }
    
    /* 指标卡片 */
    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* 警告和信息框样式 */
    .stAlert {
        border-radius: 8px;
        border: none;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* 概览卡片样式 */
    .overview-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        transition: transform 0.2s ease;
    }
    
    .overview-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .overview-card h3 {
        color: #667eea;
        margin-bottom: 0.5rem;
        font-size: 1.2rem;
    }
    
    .overview-card p {
        color: #6c757d;
        margin-bottom: 0;
        font-size: 0.9rem;
    }
    
    /* 状态指示器 */
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online {
        background-color: #28a745;
    }
    
    .status-warning {
        background-color: #ffc107;
    }
    
    .status-offline {
        background-color: #dc3545;
    }
    
    /* 响应式设计 */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .config-card {
            padding: 1rem;
        }
        
        .overview-card {
            padding: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
