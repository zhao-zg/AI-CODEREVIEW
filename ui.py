#!/usr/bin/env python3
"""
AI-CodeReview 代码审查仪表板
重构后的主UI文件 - 模块化设计
"""
import streamlit as st
import signal
import sys
import os
import atexit
from ui_components.config import setup_page_config, apply_custom_css
from ui_components.auth import check_authentication, login_sidebar, quick_login_button
from ui_components.pages import data_analysis_page, env_management_page
from biz.utils.config_manager import ConfigManager

# 信号处理和优雅关闭
def signal_handler(signum, frame):
    """处理系统信号，优雅关闭应用"""
    print(f"\n收到信号 {signum}，正在优雅关闭 AI-CodeReview UI...")
    cleanup_resources()
    print("AI-CodeReview UI 已安全关闭")
    sys.exit(0)

def cleanup_resources():
    """清理资源"""
    try:
        # 清理Streamlit缓存
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        if hasattr(st, 'cache_resource'):
            st.cache_resource.clear()
        
        # 清理临时文件
        temp_files = ['ui_startup.log', '.streamlit/config.toml']
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
        print("资源清理完成")
    except Exception as e:
        print(f"资源清理时出现错误: {e}")

# 信号处理和优雅关闭 - 仅在合适的环境中注册
def register_signal_handlers():
    """在合适的环境中注册信号处理器"""
    try:
        import threading
        import sys
        
        # 检查是否在主线程和主解释器中
        is_main_thread = threading.current_thread() is threading.main_thread()
        is_main_interpreter = hasattr(sys, '_getframe')
        
        # 检查是否在Streamlit环境中（Streamlit有自己的信号处理）
        is_streamlit_env = any(key.startswith('STREAMLIT_') for key in os.environ.keys()) or \
                          'streamlit' in sys.modules
        
        if is_main_thread and is_main_interpreter and not is_streamlit_env:
            signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
            print("✅ 信号处理器已注册")
        else:
            reason = []
            if not is_main_thread:
                reason.append("非主线程")
            if not is_main_interpreter:
                reason.append("非主解释器")
            if is_streamlit_env:
                reason.append("Streamlit环境")
            print(f"⚠️ 跳过信号处理器注册 ({', '.join(reason)})")
    except Exception as e:
        print(f"⚠️ 信号处理器注册失败: {e}")

# 注册退出清理（这个可以在任何地方调用）
atexit.register(cleanup_resources)

# 设置页面配置（必须在最开始）
setup_page_config()

# 应用自定义CSS样式
apply_custom_css()

def handle_review_detail_request(query_params):
    """处理从推送消息进入的审查详情页面请求"""
    review_type = query_params.get("review_type")
    
    st.title("🔍 审查详情查看")
    
    if review_type == "mr":
        review_id = query_params.get("review_id")
        if review_id:
            show_mr_detail(review_id)
        else:
            st.error("❌ 缺少MR ID参数")
    elif review_type == "push":
        commit_sha = query_params.get("commit_sha")
        if commit_sha:
            show_push_detail(commit_sha)
        else:
            st.error("❌ 缺少Commit SHA参数")
    elif review_type == "svn":
        revision = query_params.get("revision")
        if revision:
            show_svn_detail(revision)
        else:
            st.error("❌ 缺少SVN版本号参数")
    else:
        st.error(f"❌ 不支持的审查类型: {review_type}")
    
    # 返回主页面按钮
    if st.button("🏠 返回主页面"):
        # 清除URL参数
        st.query_params.clear()
        st.rerun()

def show_mr_detail(review_id):
    """显示MR审查详情"""
    from biz.service.review_service import ReviewService
    import sqlite3
    
    try:
        conn = sqlite3.connect(ReviewService.DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mr_review_log WHERE id=?", (review_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # 解构数据库字段
            (id_, project_name, author, source_branch, target_branch, updated_at, 
             commit_messages, score, url, review_result, additions, deletions, file_details) = row
            
            st.success(f"✅ 找到MR #{review_id} 的审查记录")
            
            # 显示MR基本信息
            col1, col2 = st.columns(2)
            with col1:
                st.metric("项目名称", project_name)
                st.metric("提交者", author)
                st.metric("AI评分", f"{score}分")
            with col2:
                st.metric("源分支", source_branch)
                st.metric("目标分支", target_branch)
                st.metric("文件变更", f"+{additions or 0} -{deletions or 0}")
            
            # 显示审查结果
            st.subheader("📝 AI审查结果")
            st.markdown(review_result or "暂无审查结果")
            
            # 显示原始MR链接
            if url:
                st.markdown(f"🔗 [查看原始MR]({url})")
        else:
            st.error(f"❌ 未找到MR #{review_id} 的审查记录")
    except Exception as e:
        st.error(f"❌ 查询MR详情时出错: {e}")

def show_push_detail(commit_sha):
    """显示Push审查详情"""
    from biz.service.review_service import ReviewService
    import sqlite3
    
    try:
        conn = sqlite3.connect(ReviewService.DB_FILE)
        cursor = conn.cursor()
        # 查找包含该commit的push记录
        cursor.execute("SELECT * FROM push_review_log WHERE commit_messages LIKE ?", (f"%{commit_sha}%",))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # 解构数据库字段
            (id_, project_name, author, branch, updated_at, commit_messages, 
             score, review_result, additions, deletions, file_details) = row
            
            st.success(f"✅ 找到包含Commit {commit_sha[:8]} 的Push审查记录")
            
            # 显示Push基本信息
            col1, col2 = st.columns(2)
            with col1:
                st.metric("项目名称", project_name)
                st.metric("提交者", author)
                st.metric("AI评分", f"{score}分")
            with col2:
                st.metric("分支", branch)
                st.metric("Commit SHA", commit_sha[:12] + "...")
                st.metric("文件变更", f"+{additions or 0} -{deletions or 0}")
            
            # 显示审查结果
            st.subheader("📝 AI审查结果")
            st.markdown(review_result or "暂无审查结果")
        else:
            st.error(f"❌ 未找到包含Commit {commit_sha} 的Push审查记录")
    except Exception as e:
        st.error(f"❌ 查询Push详情时出错: {e}")

def show_svn_detail(revision):
    """显示SVN审查详情"""
    from biz.service.review_service import ReviewService
    import sqlite3
    
    try:
        conn = sqlite3.connect(ReviewService.DB_FILE)
        cursor = conn.cursor()
        # 查找SVN版本记录
        cursor.execute("SELECT * FROM version_tracker WHERE commit_sha=? OR version_hash LIKE ?", 
                      (revision, f"%{revision}%"))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # 解构数据库字段
            (id_, project_name, version_hash, commit_sha, author, branch, file_paths, changes_hash,
             review_type_db, reviewed_at, review_result, score, created_at, commit_message, 
             commit_date, additions_count, deletions_count, file_details) = row
            
            st.success(f"✅ 找到SVN r{revision} 的审查记录")
            
            # 显示SVN基本信息
            col1, col2 = st.columns(2)
            with col1:
                st.metric("项目名称", project_name)
                st.metric("提交者", author)
                st.metric("AI评分", f"{score}分")
            with col2:
                st.metric("SVN版本", f"r{revision}")
                st.metric("SVN路径", file_paths or "未知")
                st.metric("文件变更", f"+{additions_count or 0} -{deletions_count or 0}")
            
            # 显示提交信息
            st.subheader("💬 提交信息")
            st.text(commit_message or "无提交信息")
            
            # 显示审查结果
            st.subheader("📝 AI审查结果")
            st.markdown(review_result or "暂无审查结果")
        else:
            st.error(f"❌ 未找到SVN r{revision} 的审查记录")
    except Exception as e:
        st.error(f"❌ 查询SVN详情时出错: {e}")

def main_dashboard():
    """主仪表板（无首页）"""
    
    # 检查并恢复登录状态（支持页面刷新后保持登录）
    check_authentication()
    
    # 检查URL参数，处理从推送消息进入的详情页面请求
    query_params = st.query_params
    if "review_type" in query_params:
        handle_review_detail_request(query_params)
        return

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
        
        # 管理员登录/用户菜单
        if not st.session_state.get("authenticated", False):
            # 未登录时显示登录组件
            login_sidebar()
        else:
            # 已登录时显示用户菜单
            st.markdown("---")
            st.markdown(f"### 👤 欢迎, {st.session_state.get('username', 'Admin')}")
            if st.button("� 注销登录", use_container_width=True, key="sidebar_logout"):
                st.session_state["authenticated"] = False
                st.session_state.pop("username", None)
                
                # 清理URL参数
                if "auto_login" in st.query_params:
                    del st.query_params["auto_login"]
                if "user" in st.query_params:
                    del st.query_params["user"]
                
                # 清除登录状态
                from ui_components.auth import clear_login_state
                clear_login_state()
                
                st.rerun()
        
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
            st.warning("⚠️ 需要管理员权限访问配置管理")
            st.markdown("---")
            # 显示一键登录按钮
            quick_login_button()
    else:  # 数据分析页面
        data_analysis_page()

def main():
    """主函数 - 改进版，包含异常处理和环境检测"""
    try:
        # 输出启动信息
        print("🚀 AI-CodeReview UI 正在启动...")
        print(f"📝 当前工作目录: {os.getcwd()}")
        print(f"🐍 Python版本: {sys.version}")
        
        # 检测运行环境
        import threading
        is_main_thread = threading.current_thread() is threading.main_thread()
        is_streamlit_env = any(key.startswith('STREAMLIT_') for key in os.environ.keys()) or \
                          'streamlit' in sys.modules
        
        print(f"🔍 运行环境检测: 主线程={is_main_thread}, Streamlit环境={is_streamlit_env}")
        
        # 尝试注册信号处理器（根据环境自动判断）
        register_signal_handlers()
        
        # 直接显示主仪表板，登录组件集成在侧边栏中
        main_dashboard()
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断，正在关闭...")
        cleanup_resources()
        sys.exit(0)
    except Exception as e:
        error_info = f"\n❌ 应用运行时出现错误: {e}"
        print(error_info)
        # 在Streamlit中也显示错误
        if 'streamlit' in sys.modules:
            import streamlit as st
            st.error(f"应用启动错误: {e}")
            st.info("请检查控制台输出获取详细错误信息")
        cleanup_resources()
        # 在Streamlit环境中不要直接退出，避免页面崩溃
        if not any(key.startswith('STREAMLIT_') for key in os.environ.keys()):
            sys.exit(1)

if __name__ == "__main__":
    import os
    import sys
    import subprocess
    from biz.utils.default_config import get_env_with_default
    
    # 检查是否在streamlit环境中运行
    # 通过检查环境变量和模块来判断
    is_streamlit_run = False
    
    # 方法1：检查是否有streamlit相关的环境变量
    if any(key.startswith('STREAMLIT_') for key in os.environ.keys()):
        is_streamlit_run = True
    
    # 方法2：检查调用栈中是否有streamlit
    try:
        import traceback
        stack = traceback.format_stack()
        if any('streamlit' in frame for frame in stack):
            is_streamlit_run = True
    except:
        pass
    
    # 方法3：检查命令行参数
    if len(sys.argv) > 1 and any('streamlit' in arg for arg in sys.argv):
        is_streamlit_run = True
    
    if not is_streamlit_run:
        # 直接运行ui.py时，自动启动streamlit
        ui_port = get_env_with_default('UI_PORT', '5002')
        
        print(f"启动 AI-CodeReview UI 服务...")
        print(f"地址: http://0.0.0.0:{ui_port}")
        print(f"端口配置来源: UI_PORT={ui_port}")
        print(f"浏览器访问: http://localhost:{ui_port}")
        
        # 构建streamlit命令
        cmd = [
            sys.executable, '-m', 'streamlit', 'run', __file__,
            '--server.port', str(ui_port),
            '--server.address', '0.0.0.0',
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false'
        ]
        
        # 执行streamlit命令
        try:
            print("正在启动Streamlit服务...")
            # 使用os.execv来替换当前进程，避免循环
            os.execv(sys.executable, cmd)
        except Exception as e:
            print(f"启动失败: {e}")
            sys.exit(1)
    else:
        # 通过streamlit启动的正常流程
        main()
