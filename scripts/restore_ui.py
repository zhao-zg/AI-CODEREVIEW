#!/usr/bin/env python3
"""
UI文件恢复和重构脚本
恢复配置管理功能并建议模块化拆分
"""

import os
import shutil
from pathlib import Path

def create_ui_modules():
    """创建模块化的UI文件结构"""
    
    # 创建ui模块目录
    ui_dir = Path("ui_modules")
    ui_dir.mkdir(exist_ok=True)
    
    # 1. 认证模块
    auth_module = '''#!/usr/bin/env python3
"""
认证模块
"""
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv("conf/.env")

# 从环境变量中读取用户名和密码
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}

def authenticate(username, password):
    """登录验证函数"""
    return username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password

def login_page():
    """登录页面"""
    # 页面标题
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; margin-bottom: 2rem; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 2.5rem;">🤖 AI 代码审查系统</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">智能代码质量监控与分析平台</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 登录表单
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 系统登录")
            with st.form("login_form"):
                username = st.text_input("👤 用户名", placeholder="请输入用户名")
                password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
                
                submit_button = st.form_submit_button("🚀 登录", use_container_width=True)
                
                if submit_button:
                    if authenticate(username, password):
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username
                        st.success("✅ 登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误")
    
    # 页面底部信息
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🔧 **功能特性**\\n多平台代码审查")
    with col2:
        st.info("📊 **数据分析**\\n质量趋势统计")
    with col3:
        st.info("⚙️ **配置管理**\\n灵活参数设置")
'''
    
    # 2. 配置管理模块
    config_module = '''#!/usr/bin/env python3
"""
配置管理模块UI
"""
import streamlit as st
import json
import os
from biz.utils.config_manager import ConfigManager

def show_config_management():
    """显示配置管理页面"""
    st.markdown("### ⚙️ 系统配置管理")
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 配置选项卡
    config_tab1, config_tab2, config_tab3 = st.tabs(["🔧 环境配置", "🎨 界面配置", "📝 AI提示模板"])
    
    with config_tab1:
        show_env_config(config_manager)
    
    with config_tab2:
        show_dashboard_config(config_manager)
    
    with config_tab3:
        show_prompt_config(config_manager)

def show_env_config(config_manager):
    """显示环境配置"""
    st.markdown("#### 🔧 环境变量配置")
    
    # 获取当前配置
    env_config = config_manager.get_env_config()
    
    # 配置分组
    with st.expander("🤖 AI模型配置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            llm_provider = st.selectbox(
                "LLM提供商", 
                options=["deepseek", "openai", "zhipuai", "qwen", "ollama"],
                index=["deepseek", "openai", "zhipuai", "qwen", "ollama"].index(env_config.get("LLM_PROVIDER", "deepseek")),
                key="llm_provider"
            )
        
        with col2:
            server_port = st.number_input(
                "服务端口", 
                value=int(env_config.get("SERVER_PORT", "5001")), 
                key="server_port"
            )
        
        # 根据选择的LLM提供商显示相应配置
        if llm_provider == "deepseek":
            deepseek_api_key = st.text_input(
                "DeepSeek API Key", 
                value=env_config.get("DEEPSEEK_API_KEY", ""), 
                type="password",
                key="deepseek_api_key"
            )
            deepseek_api_base = st.text_input(
                "DeepSeek API Base URL", 
                value=env_config.get("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com"),
                key="deepseek_api_base"
            )
            deepseek_model = st.text_input(
                "DeepSeek 模型", 
                value=env_config.get("DEEPSEEK_API_MODEL", "deepseek-chat"),
                key="deepseek_model"
            )
        elif llm_provider == "ollama":
            ollama_api_base = st.text_input(
                "Ollama API Base URL", 
                value=env_config.get("OLLAMA_API_BASE_URL", "http://127.0.0.1:11434"),
                key="ollama_api_base"
            )
            ollama_model = st.text_input(
                "Ollama 模型", 
                value=env_config.get("OLLAMA_API_MODEL", "deepseek-r1:latest"),
                key="ollama_model"
            )
    
    # 审查配置
    with st.expander("📋 代码审查配置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            supported_extensions = st.text_input(
                "支持的文件扩展名", 
                value=env_config.get("SUPPORTED_EXTENSIONS", ".py,.js,.ts,.java,.cpp,.c,.h,.cs,.php,.rb,.go,.rs,.swift,.kt,.scala,.lua"),
                key="supported_extensions_config",
                help="用逗号分隔的文件扩展名列表"
            )
            review_max_tokens = st.number_input(
                "Review最大Token限制", 
                value=int(env_config.get("REVIEW_MAX_TOKENS", "10000")), 
                key="review_max_tokens"
            )
        
        with col2:
            review_style = st.selectbox(
                "Review风格", 
                options=["professional", "sarcastic", "gentle", "humorous"],
                index=["professional", "sarcastic", "gentle", "humorous"].index(env_config.get("REVIEW_STYLE", "professional")),
                key="review_style"
            )
            
            push_review_enabled = st.checkbox(
                "启用Push Review功能", 
                value=bool(int(env_config.get("PUSH_REVIEW_ENABLED", "1"))), 
                key="push_review"
            )
    
    # SVN配置
    with st.expander("📂 SVN配置", expanded=False):
        svn_check_enabled = st.checkbox(
            "启用SVN代码审查", 
            value=bool(int(env_config.get("SVN_CHECK_ENABLED", "0"))), 
            key="svn_check_enabled"
        )
        
        if svn_check_enabled:
            svn_repos = st.text_area(
                "SVN仓库配置 (JSON格式)", 
                value=env_config.get("SVN_REPOSITORIES", "[]"),
                height=100,
                key="svn_repos"
            )
    
    # 保存配置按钮
    if st.button("💾 保存环境配置", type="primary", use_container_width=True):
        new_config = {
            "SERVER_PORT": str(server_port),
            "LLM_PROVIDER": llm_provider,
            "SUPPORTED_EXTENSIONS": supported_extensions,
            "REVIEW_MAX_TOKENS": str(review_max_tokens),
            "REVIEW_STYLE": review_style,
            "PUSH_REVIEW_ENABLED": "1" if push_review_enabled else "0",
            "SVN_CHECK_ENABLED": "1" if svn_check_enabled else "0",
        }
        
        # 添加特定LLM提供商的配置
        if llm_provider == "deepseek":
            new_config.update({
                "DEEPSEEK_API_KEY": deepseek_api_key,
                "DEEPSEEK_API_BASE_URL": deepseek_api_base,
                "DEEPSEEK_API_MODEL": deepseek_model,
            })
        elif llm_provider == "ollama":
            new_config.update({
                "OLLAMA_API_BASE_URL": ollama_api_base,
                "OLLAMA_API_MODEL": ollama_model,
            })
        
        if svn_check_enabled:
            new_config["SVN_REPOSITORIES"] = svn_repos
        
        if config_manager.save_env_config(new_config):
            st.success("✅ 环境配置保存成功！")
        else:
            st.error("❌ 环境配置保存失败！")

def show_dashboard_config(config_manager):
    """显示界面配置"""
    st.markdown("#### 🎨 界面配置")
    st.info("界面配置功能开发中...")

def show_prompt_config(config_manager):
    """显示AI提示模板配置"""
    st.markdown("#### 📝 AI提示模板配置")
    
    prompt_config = config_manager.get_prompt_config()
    
    # 代码审查提示模板
    code_review_prompt = st.text_area(
        "代码审查提示模板",
        value=prompt_config.get("code_review", "请对以下代码进行详细审查..."),
        height=200,
        key="code_review_prompt"
    )
    
    # 保存按钮
    if st.button("💾 保存提示模板", type="primary"):
        new_prompt_config = {
            "code_review": code_review_prompt
        }
        
        if config_manager.save_prompt_config(new_prompt_config):
            st.success("✅ 提示模板保存成功！")
        else:
            st.error("❌ 提示模板保存失败！")
'''
    
    # 3. 数据分析模块
    data_analysis_module = '''#!/usr/bin/env python3
"""
数据分析模块UI
"""
import streamlit as st
import datetime
import pandas as pd
from biz.service.review_service import ReviewService

def show_data_analysis():
    """显示数据分析页面"""
    # 页面标题和说明
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">📊 代码审查数据分析中心</h2>
        <p style="color: #f0f0f0; margin: 10px 0 0 0;">深入分析代码审查质量，洞察团队开发效率</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 获取审查类型统计
    review_stats = ReviewService().get_review_type_stats()
    
    # 总体统计概览
    st.markdown("#### 📈 总体统计概览")
    overview_col1, overview_col2, overview_col3, overview_col4, overview_col5 = st.columns(5)
    
    total_reviews = sum([
        review_stats.get('mr_count', 0),
        review_stats.get('push_count', 0), 
        review_stats.get('svn_count', 0),
        review_stats.get('github_count', 0),
        review_stats.get('gitlab_count', 0)
    ])
    
    with overview_col1:
        st.metric(
            label="📋 总审查数",
            value=total_reviews,
            help="所有类型的审查总数"
        )
    
    with overview_col2:
        st.metric(
            label="🔀 MR审查",
            value=review_stats.get('mr_count', 0),
            delta=f"{review_stats.get('mr_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="GitLab合并请求审查数量"
        )
    
    with overview_col3:
        st.metric(
            label="📤 Push审查", 
            value=review_stats.get('push_count', 0),
            delta=f"{review_stats.get('push_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="Git推送审查数量"
        )
    
    with overview_col4:
        st.metric(
            label="📂 SVN审查",
            value=review_stats.get('svn_count', 0),
            delta=f"{review_stats.get('svn_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="SVN提交审查数量"
        )
    
    with overview_col5:
        st.metric(
            label="🐙 GitHub审查",
            value=review_stats.get('github_count', 0),
            delta=f"{review_stats.get('github_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="GitHub相关审查数量"
        )
    
    # 添加性能提示
    if total_reviews > 1000:
        st.warning("⚡ 数据量较大，加载可能需要一些时间，请耐心等待...")
    elif total_reviews == 0:
        st.error("📭 暂无审查数据，请先进行一些代码审查或检查数据库连接。")
    
    st.markdown("---")
    st.markdown("#### 🎯 选择分析类型")
    
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
            "📊 选择要分析的审查数据类型",
            options=available_types,
            format_func=lambda x: type_labels.get(x, x),
            key="main_review_type_selector",
            help="选择不同类型的审查数据进行深入分析"
        )
    
    with col2:
        if st.button("🔄 刷新统计", use_container_width=True, key="refresh_stats"):
            st.cache_data.clear()
            st_rerun()
'''
    
    # 写入文件
    modules = {
        "auth.py": auth_module,
        "config_ui.py": config_module,
        "data_analysis.py": data_analysis_module
    }
    
    for filename, content in modules.items():
        with open(ui_dir / filename, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"✅ UI模块已创建在 {ui_dir} 目录中")
    
    return ui_dir

def create_restored_ui():
    """创建恢复后的完整UI文件"""
    
    restored_ui_content = '''#!/usr/bin/env python3
"""
多类型代码审查UI - 支持SVN、GitLab、GitHub
恢复版本：包含完整的配置管理功能
"""

import datetime
import math
import os
import sys
import json

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

def st_rerun():
    """兼容性函数：支持不同版本的Streamlit"""
    if hasattr(st, 'rerun'):
        st.rerun()
    elif hasattr(st, 'experimental_rerun'):
        st.experimental_rerun()
    else:
        # 对于更老的版本，抛出异常提示升级
        raise RuntimeError("请升级Streamlit到支持rerun功能的版本")

# 工具函数
def authenticate(username, password):
    """登录验证函数"""
    return username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password

def login_page():
    """登录页面"""
    # 页面标题
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; margin-bottom: 2rem; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 2.5rem;">🤖 AI 代码审查系统</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">智能代码质量监控与分析平台</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 登录表单
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 系统登录")
            with st.form("login_form"):
                username = st.text_input("👤 用户名", placeholder="请输入用户名")
                password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
                
                submit_button = st.form_submit_button("🚀 登录", use_container_width=True)
                
                if submit_button:
                    if authenticate(username, password):
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username
                        st.success("✅ 登录成功！")
                        st_rerun()
                    else:
                        st.error("❌ 用户名或密码错误")

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

def show_config_management():
    """显示配置管理页面"""
    st.markdown("### ⚙️ 系统配置管理")
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 配置选项卡
    config_tab1, config_tab2, config_tab3 = st.tabs(["🔧 环境配置", "🎨 界面配置", "📝 AI提示模板"])
    
    with config_tab1:
        show_env_config(config_manager)
    
    with config_tab2:
        show_dashboard_config(config_manager)
    
    with config_tab3:
        show_prompt_config(config_manager)

def show_env_config(config_manager):
    """显示环境配置"""
    st.markdown("#### 🔧 环境变量配置")
    
    # 获取当前配置
    env_config = config_manager.get_env_config()
    
    # 配置分组
    with st.expander("🤖 AI模型配置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            llm_provider = st.selectbox(
                "LLM提供商", 
                options=["deepseek", "openai", "zhipuai", "qwen", "ollama"],
                index=["deepseek", "openai", "zhipuai", "qwen", "ollama"].index(env_config.get("LLM_PROVIDER", "deepseek")),
                key="llm_provider"
            )
        
        with col2:
            server_port = st.number_input(
                "服务端口", 
                value=int(env_config.get("SERVER_PORT", "5001")), 
                key="server_port"
            )
        
        # 根据选择的LLM提供商显示相应配置
        if llm_provider == "deepseek":
            deepseek_api_key = st.text_input(
                "DeepSeek API Key", 
                value=env_config.get("DEEPSEEK_API_KEY", ""), 
                type="password",
                key="deepseek_api_key"
            )
            deepseek_api_base = st.text_input(
                "DeepSeek API Base URL", 
                value=env_config.get("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com"),
                key="deepseek_api_base"
            )
            deepseek_model = st.text_input(
                "DeepSeek 模型", 
                value=env_config.get("DEEPSEEK_API_MODEL", "deepseek-chat"),
                key="deepseek_model"
            )
        elif llm_provider == "ollama":
            ollama_api_base = st.text_input(
                "Ollama API Base URL", 
                value=env_config.get("OLLAMA_API_BASE_URL", "http://127.0.0.1:11434"),
                key="ollama_api_base"
            )
            ollama_model = st.text_input(
                "Ollama 模型", 
                value=env_config.get("OLLAMA_API_MODEL", "deepseek-r1:latest"),
                key="ollama_model"
            )
    
    # 审查配置
    with st.expander("📋 代码审查配置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            supported_extensions = st.text_input(
                "支持的文件扩展名", 
                value=env_config.get("SUPPORTED_EXTENSIONS", ".py,.js,.ts,.java,.cpp,.c,.h,.cs,.php,.rb,.go,.rs,.swift,.kt,.scala,.lua"),
                key="supported_extensions_config",
                help="用逗号分隔的文件扩展名列表"
            )
            review_max_tokens = st.number_input(
                "Review最大Token限制", 
                value=int(env_config.get("REVIEW_MAX_TOKENS", "10000")), 
                key="review_max_tokens"
            )
        
        with col2:
            review_style = st.selectbox(
                "Review风格", 
                options=["professional", "sarcastic", "gentle", "humorous"],
                index=["professional", "sarcastic", "gentle", "humorous"].index(env_config.get("REVIEW_STYLE", "professional")),
                key="review_style"
            )
            
            push_review_enabled = st.checkbox(
                "启用Push Review功能", 
                value=bool(int(env_config.get("PUSH_REVIEW_ENABLED", "1"))), 
                key="push_review"
            )
    
    # SVN配置
    with st.expander("📂 SVN配置", expanded=False):
        svn_check_enabled = st.checkbox(
            "启用SVN代码审查", 
            value=bool(int(env_config.get("SVN_CHECK_ENABLED", "0"))), 
            key="svn_check_enabled"
        )
        
        if svn_check_enabled:
            svn_repos = st.text_area(
                "SVN仓库配置 (JSON格式)", 
                value=env_config.get("SVN_REPOSITORIES", "[]"),
                height=100,
                key="svn_repos"
            )
    
    # 保存配置按钮
    if st.button("💾 保存环境配置", type="primary", use_container_width=True):
        new_config = {
            "SERVER_PORT": str(server_port),
            "LLM_PROVIDER": llm_provider,
            "SUPPORTED_EXTENSIONS": supported_extensions,
            "REVIEW_MAX_TOKENS": str(review_max_tokens),
            "REVIEW_STYLE": review_style,
            "PUSH_REVIEW_ENABLED": "1" if push_review_enabled else "0",
            "SVN_CHECK_ENABLED": "1" if svn_check_enabled else "0",
        }
        
        # 添加特定LLM提供商的配置
        if llm_provider == "deepseek":
            new_config.update({
                "DEEPSEEK_API_KEY": deepseek_api_key,
                "DEEPSEEK_API_BASE_URL": deepseek_api_base,
                "DEEPSEEK_API_MODEL": deepseek_model,
            })
        elif llm_provider == "ollama":
            new_config.update({
                "OLLAMA_API_BASE_URL": ollama_api_base,
                "OLLAMA_API_MODEL": ollama_model,
            })
        
        if svn_check_enabled:
            new_config["SVN_REPOSITORIES"] = svn_repos
        
        if config_manager.save_env_config(new_config):
            st.success("✅ 环境配置保存成功！")
        else:
            st.error("❌ 环境配置保存失败！")

def show_dashboard_config(config_manager):
    """显示界面配置"""
    st.markdown("#### 🎨 界面配置")
    st.info("界面配置功能开发中...")

def show_prompt_config(config_manager):
    """显示AI提示模板配置"""
    st.markdown("#### 📝 AI提示模板配置")
    
    prompt_config = config_manager.get_prompt_config()
    
    # 代码审查提示模板
    code_review_prompt = st.text_area(
        "代码审查提示模板",
        value=prompt_config.get("code_review", "请对以下代码进行详细审查..."),
        height=200,
        key="code_review_prompt"
    )
    
    # 保存按钮
    if st.button("💾 保存提示模板", type="primary"):
        new_prompt_config = {
            "code_review": code_review_prompt
        }
        
        if config_manager.save_prompt_config(new_prompt_config):
            st.success("✅ 提示模板保存成功！")
        else:
            st.error("❌ 提示模板保存失败！")

def show_data_analysis():
    """显示数据分析页面"""
    # 页面标题和说明
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">📊 代码审查数据分析中心</h2>
        <p style="color: #f0f0f0; margin: 10px 0 0 0;">深入分析代码审查质量，洞察团队开发效率</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 获取审查类型统计
    review_stats = ReviewService().get_review_type_stats()
    
    # 总体统计概览
    st.markdown("#### 📈 总体统计概览")
    overview_col1, overview_col2, overview_col3, overview_col4, overview_col5 = st.columns(5)
    
    total_reviews = sum([
        review_stats.get('mr_count', 0),
        review_stats.get('push_count', 0), 
        review_stats.get('svn_count', 0),
        review_stats.get('github_count', 0),
        review_stats.get('gitlab_count', 0)
    ])
    
    with overview_col1:
        st.metric(
            label="📋 总审查数",
            value=total_reviews,
            help="所有类型的审查总数"
        )
    
    with overview_col2:
        st.metric(
            label="🔀 MR审查",
            value=review_stats.get('mr_count', 0),
            delta=f"{review_stats.get('mr_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="GitLab合并请求审查数量"
        )
    
    with overview_col3:
        st.metric(
            label="📤 Push审查", 
            value=review_stats.get('push_count', 0),
            delta=f"{review_stats.get('push_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="Git推送审查数量"
        )
    
    with overview_col4:
        st.metric(
            label="📂 SVN审查",
            value=review_stats.get('svn_count', 0),
            delta=f"{review_stats.get('svn_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="SVN提交审查数量"
        )
    
    with overview_col5:
        st.metric(
            label="🐙 GitHub审查",
            value=review_stats.get('github_count', 0),
            delta=f"{review_stats.get('github_count', 0)/max(total_reviews, 1)*100:.1f}%",
            help="GitHub相关审查数量"
        )
    
    # 添加性能提示
    if total_reviews > 1000:
        st.warning("⚡ 数据量较大，加载可能需要一些时间，请耐心等待...")
    elif total_reviews == 0:
        st.error("📭 暂无审查数据，请先进行一些代码审查或检查数据库连接。")
    
    st.markdown("---")
    st.markdown("#### 🎯 选择分析类型")
    
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
            "📊 选择要分析的审查数据类型",
            options=available_types,
            format_func=lambda x: type_labels.get(x, x),
            key="main_review_type_selector",
            help="选择不同类型的审查数据进行深入分析"
        )
    
    with col2:
        if st.button("🔄 刷新统计", use_container_width=True, key="refresh_stats"):
            st.cache_data.clear()
            st_rerun()
    
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

def display_legacy_data(review_type):
    """显示传统数据（MR/Push）"""
    st.info(f"📋 {review_type.upper()} 数据显示功能开发中...")

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
            if not df.empty:
                unique_authors = df['author'].nunique()
                st.metric("👥 开发者数量", unique_authors)
            else:
                st.metric("👥 开发者数量", "0")
        
        with col4:
            if not df.empty:
                unique_projects = df['project_name'].nunique()
                st.metric("📦 项目数量", unique_projects)
            else:
                st.metric("📦 项目数量", "0")
        
        # 数据表格
        if not df.empty:
            st.markdown("##### 📊 审查数据表格")
            st.markdown("*点击任意行查看详细审查报告*")
            
            # 显示数据表格
            display_df = df[['project_name', 'author', 'formatted_time', 'score', 'commit_sha', 'file_paths']].copy()
            
            # 配置列
            if review_type == 'svn':
                column_config = {
                    "project_name": st.column_config.TextColumn("项目名称", width="medium"),
                    "author": st.column_config.TextColumn("作者", width="small"),
                    "formatted_time": st.column_config.TextColumn("提交时间", width="medium"),
                    "score": st.column_config.ProgressColumn("质量分数", format="%d", min_value=0, max_value=100, width="small"),
                    "commit_sha": st.column_config.TextColumn("提交SHA", width="medium"),
                    "file_paths": st.column_config.TextColumn("文件路径", width="large"),
                }
            else:
                column_config = {
                    "project_name": st.column_config.TextColumn("项目名称", width="medium"),
                    "author": st.column_config.TextColumn("作者", width="small"),
                    "formatted_time": st.column_config.TextColumn("提交时间", width="medium"),
                    "score": st.column_config.ProgressColumn("质量分数", format="%d", min_value=0, max_value=100, width="small"),
                    "commit_sha": st.column_config.TextColumn("提交SHA", width="medium"),
                }
            
            event = st.dataframe(
                display_df,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
    except Exception as e:
        st.error(f"❌ 获取 {review_type} 数据失败: {e}")

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
        
        # 页面选择
        page = st.radio("选择页面", ["📊 数据分析", "⚙️ 配置管理"], key="page_selection")
        
        st.markdown("---")
        if st.button("🔄 刷新数据", use_container_width=True, key="refresh_all"):
            st.cache_data.clear()
            st_rerun()
        
        st.markdown("---")
        if st.button("🚪 注销", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state.pop("username", None)
            st_rerun()
    
    # 根据选择显示不同页面
    if page == "📊 数据分析":
        show_data_analysis()
    elif page == "⚙️ 配置管理":
        show_config_management()

# 初始化session state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# 主程序逻辑
if not st.session_state["authenticated"]:
    login_page()
else:
    main_dashboard()
'''
    
    with open("ui_restored.py", 'w', encoding='utf-8') as f:
        f.write(restored_ui_content)
    
    print("✅ 恢复的UI文件已创建: ui_restored.py")
    print("✅ 包含完整的配置管理功能")

if __name__ == "__main__":
    print("🚀 开始UI文件恢复和重构...")
    
    # 创建模块化文件
    ui_dir = create_ui_modules()
    
    # 创建恢复的完整UI文件
    create_restored_ui()
    
    print("\n📋 文件结构建议:")
    print("1. ui_restored.py - 恢复后的完整UI文件")
    print("2. ui_modules/ - 模块化的UI组件:")
    print("   - auth.py - 认证模块")
    print("   - config_ui.py - 配置管理UI")
    print("   - data_analysis.py - 数据分析模块")
    
    print("\n🔧 下一步操作建议:")
    print("1. 备份当前的ui.py: mv ui.py ui_old.py")
    print("2. 使用恢复的文件: mv ui_restored.py ui.py")
    print("3. 测试功能: streamlit run ui.py")
    print("4. 考虑逐步迁移到模块化结构")
    
    print("\n✅ UI恢复和重构完成!")
