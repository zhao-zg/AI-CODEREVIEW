#!/usr/bin/env python3
"""
AI-CodeReview 代码审查仪表板
重构后的主UI文件 - 模块化设计
"""
import streamlit as st
from ui_components.config import setup_page_config, apply_custom_css
from ui_components.auth import check_authentication, login_page, user_menu
from ui_components.pages import data_analysis_page, env_management_page
from biz.utils.config_manager import ConfigManager

# 设置页面配置（必须在最开始）
setup_page_config()

# 应用自定义CSS样式
apply_custom_css()

def main_dashboard():
    """主仪表板（无首页）"""
    
    # 在页面顶部右侧显示用户菜单
    user_menu()
    
    # 侧边栏 - 简化布局
    with st.sidebar:
        # 功能菜单
        st.markdown("### 🛠️ 系统功能")
        
        # 页面导航 - 仅登录后显示配置管理
        page_options = ["📊 数据分析"]
        if st.session_state.get("authenticated", False):
            page_options.append("⚙️ 配置管理")
        page = st.radio(
            "选择功能模块",
            page_options,
            key="page_selector",
            help="选择要访问的功能模块"
        )
        
        # 管理员登录入口（未登录时显示）
        if not st.session_state.get("authenticated", False):
            if st.button("🔑 管理员登录", use_container_width=True):
                st.session_state["page"] = "/admin"
        
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
            **📊 数据分析**: 查看代码审查统计和详细记录
            
            **⚙️ 配置管理**: 管理AI模型、平台开关等系统配置
            
            **用户操作**: 
            - 👤 点击右上角用户名可注销登录
            """)
    
    # 根据选择的页面显示内容
    if page == "⚙️ 配置管理":
        if st.session_state.get("authenticated", False):
            env_management_page()
        else:
            st.warning("请先登录管理员账号")
    else:  # 数据分析页面
        data_analysis_page()

def main():
    """主函数"""
    # 页面跳转控制
    page = st.session_state.get("page", "main")
    if page == "/admin":
        login_page()
        # 登录成功后自动跳转回主页面
        if st.session_state.get("authenticated", False):
            st.session_state["page"] = "main"
            st.rerun()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
