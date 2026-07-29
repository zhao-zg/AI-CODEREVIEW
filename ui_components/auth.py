"""
认证相关功能模块 - 基于配置文件的认证
"""

import os
import json
import hashlib
import tempfile
import pandas as pd
import streamlit as st
from biz.utils.config_manager import ConfigManager

def authenticate(username, password):
    """基于配置文件的用户认证"""
    try:
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        
        # 从环境配置中获取Dashboard账户信息
        dashboard_username = env_config.get('DASHBOARD_USER', 'admin')
        dashboard_password = env_config.get('DASHBOARD_PASSWORD', 'admin')
        
        return username == dashboard_username and password == dashboard_password
    except Exception as e:
        st.error(f"认证配置读取失败: {e}")
        # 使用默认认证作为fallback
        return username == "admin" and password == "admin"

def get_session_file_path():
    """
    获取当前会话的持久化文件路径
    基于Streamlit的session ID创建唯一标识
    """
    try:
        # 获取Streamlit的session_id
        from streamlit.runtime import get_instance
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        
        runtime = get_instance()
        if runtime and runtime.is_ready:
            session_id = get_script_run_ctx().session_id if get_script_run_ctx() else None
            if session_id:
                # 使用session_id的hash作为文件名
                session_hash = hashlib.md5(session_id.encode()).hexdigest()[:16]
                return os.path.join(tempfile.gettempdir(), f"ai_codereview_session_{session_hash}.json")
    except:
        pass
    
    # 如果无法获取session_id，使用fallback方案
    fallback_id = str(hash(str(st.session_state)))[:16].replace('-', '0')
    return os.path.join(tempfile.gettempdir(), f"ai_codereview_session_{fallback_id}.json")

def save_login_state(username):
    """保存登录状态到持久化文件"""
    try:
        session_file = get_session_file_path()
        login_data = {
            'authenticated': True,
            'username': username,
            'timestamp': str(pd.Timestamp.now())
        }
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(login_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        st.error(f"保存登录状态失败: {e}")
        return False

def load_login_state():
    """从持久化文件加载登录状态"""
    try:
        session_file = get_session_file_path()
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                login_data = json.load(f)
            
            # 检查文件是否过期(24小时)
            import pandas as pd
            if 'timestamp' in login_data:
                saved_time = pd.Timestamp(login_data['timestamp'])
                current_time = pd.Timestamp.now()
                if (current_time - saved_time).total_seconds() > 24 * 3600:
                    # 文件过期，删除
                    clear_login_state()
                    return None
            
            return login_data
    except Exception as e:
        # 如果文件损坏，清除它
        clear_login_state()
        return None

def clear_login_state():
    """清除登录状态文件"""
    try:
        session_file = get_session_file_path()
        if os.path.exists(session_file):
            os.remove(session_file)
    except Exception:
        pass

def quick_login_button():
    """一键登录按钮"""
    if not st.session_state.get("authenticated", False):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔐 管理员登录", use_container_width=True, key="quick_login_btn"):
                # 使用默认管理员账户直接登录
                try:
                    from biz.utils.config_manager import ConfigManager
                    config_manager = ConfigManager()
                    env_config = config_manager.get_env_config()
                    
                    # 从环境配置中获取Dashboard账户信息
                    dashboard_username = env_config.get('DASHBOARD_USER', 'admin')
                    
                    # 直接设置登录状态
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = dashboard_username
                    
                    # 保存登录状态
                    save_login_state(dashboard_username)
                    
                    # 设置URL参数以支持session持久化
                    st.query_params["auto_login"] = "true"
                    st.query_params["user"] = dashboard_username
                    
                    st.success("✅ 管理员登录成功！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"登录失败: {e}")

def login_sidebar():
    """侧边栏登录组件"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔐 管理员登录")
        
        with st.form("sidebar_login_form"):
            username = st.text_input("👤 用户名", key="sidebar_username")
            password = st.text_input("🔒 密码", type="password", key="sidebar_password")
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

def login_modal():
    """弹窗登录组件"""
    # 检查是否需要显示登录弹窗
    if not st.session_state.get("authenticated", False):
        # 在主页面添加登录按钮
        col1, col2, col3 = st.columns([1, 2, 1])
        with col3:
            if st.button("🔐 管理员登录", key="show_login_modal"):
                st.session_state["show_login_modal"] = True
    
    # 显示登录弹窗
    if st.session_state.get("show_login_modal", False):
        with st.container():
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("### 🔐 管理员登录")
                
                with st.form("modal_login_form"):
                    username = st.text_input("👤 用户名", key="modal_username")
                    password = st.text_input("🔒 密码", type="password", key="modal_password")
                    
                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        submitted = st.form_submit_button("🚪 登录", use_container_width=True)
                    with col_cancel:
                        cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
                
                if submitted:
                    if authenticate(username, password):
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username
                        st.session_state["show_login_modal"] = False
                        
                        # 保存登录状态
                        save_login_state(username)
                        
                        # 设置URL参数以支持session持久化
                        st.query_params["auto_login"] = "true"
                        st.query_params["user"] = username
                        
                        st.success("✅ 登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误！")
                
                if cancelled:
                    st.session_state["show_login_modal"] = False
                    st.rerun()
            
            st.markdown("---")

def login_expander():
    """展开式登录组件"""
    if not st.session_state.get("authenticated", False):
        with st.expander("🔐 管理员登录", expanded=False):
            with st.form("expander_login_form"):
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input("👤 用户名", key="expander_username")
                with col2:
                    password = st.text_input("🔒 密码", type="password", key="expander_password")
                
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

def user_menu():
    """用户菜单组件"""
    if "username" in st.session_state:
        # 创建一个不可见的容器来放置用户菜单
        col1, col2 = st.columns([5, 1])
        with col2:
            # 使用popover显示用户菜单
            with st.popover(f"👤 {st.session_state['username']}", help="用户菜单"):
                if st.button("🚪 注销登录", use_container_width=True, key="logout_user_menu"):
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

def check_authentication():
    """检查认证状态"""
    # 初始化session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    
    # 初始化session计数器以支持页面刷新后的状态恢复
    if "session_counter" not in st.session_state:
        st.session_state["session_counter"] = 0
    st.session_state["session_counter"] += 1
    
    # 尝试从持久化文件恢复登录状态（页面刷新后保持登录）
    if not st.session_state["authenticated"]:
        # 先尝试从URL参数恢复
        query_params = st.query_params
        
        restored = False
        
        # 方法1：从URL参数恢复
        if "auto_login" in query_params and query_params["auto_login"] == "true" and "user" in query_params:
            username = query_params["user"]
            if username:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                restored = True
        
        # 方法2：从持久化文件恢复
        if not restored:
            saved_state = load_login_state()
            if saved_state and saved_state.get('authenticated'):
                username = saved_state.get('username')
                if username:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    restored = True
        
        # 如果成功恢复，刷新页面以更新UI
        # 注意：如果 URL 中包含 review_type 参数（从通知链接进入详情页），
        # 不触发 rerun，让脚本继续执行到详情页面处理逻辑，避免参数丢失
        if restored:
            if "review_type" in st.query_params:
                return True
            st.rerun()
    
    return st.session_state["authenticated"]

def quick_login_button():
    """一键登录按钮"""
    if not st.session_state.get("authenticated", False):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔐 管理员登录", use_container_width=True, key="quick_login_btn"):
                # 使用默认管理员账户直接登录
                try:
                    config_manager = ConfigManager()
                    env_config = config_manager.get_env_config()
                    
                    # 从环境配置中获取Dashboard账户信息
                    dashboard_username = env_config.get('DASHBOARD_USER', 'admin')
                    dashboard_password = env_config.get('DASHBOARD_PASSWORD', 'admin')
                    
                    # 直接设置登录状态
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = dashboard_username
                    
                    # 保存登录状态
                    save_login_state(dashboard_username)
                    
                    # 设置URL参数以支持session持久化
                    st.query_params["auto_login"] = "true"
                    st.query_params["user"] = dashboard_username
                    
                    st.success("✅ 管理员登录成功！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"登录失败: {e}")
