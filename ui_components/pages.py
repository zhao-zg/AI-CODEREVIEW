"""
页面组件模块
"""

import streamlit as st
import requests
import os
from dotenv import load_dotenv
from biz.utils.config_manager import ConfigManager
from .utils import get_platform_status, get_review_stats, get_available_authors, get_available_projects
from .data_display import display_version_tracking_data, display_legacy_data

def apply_config_changes():
    """应用配置更改，使其立即生效"""
    # 先加载环境变量
    load_dotenv('conf/.env')
    
    success_count = 0
    total_attempts = 0
    
    try:
        # 方法1: 尝试通过 ConfigReloader 热重载
        try:
            from biz.utils.config_reloader import ConfigReloader
            reloader = ConfigReloader()
            result = reloader.reload_all_configs()
            
            if result.get("success", False):
                success_count += 1
                st.info("✅ 配置热重载成功")
            else:
                st.warning(f"⚠️ 配置热重载部分成功: {result.get('message', '未知错误')}")
                
            total_attempts += 1
            
        except Exception as e:
            st.warning(f"⚠️ 配置热重载失败: {e}")
        
        # 方法2: 尝试通过 API 端点重载配置
        try:
            api_port = os.environ.get('API_PORT', '5001')
            api_url = f"http://localhost:{api_port}/reload-config"
            
            response = requests.post(api_url, timeout=5)
            if response.status_code == 200:
                success_count += 1
                st.info("✅ API服务配置重载成功")
            else:
                st.warning(f"⚠️ API服务配置重载失败: {response.text}")
                
            total_attempts += 1
            
        except requests.exceptions.ConnectionError:
            st.info("ℹ️ API服务不可达，可能未启动")
        except Exception as e:
            st.warning(f"⚠️ API服务配置重载失败: {e}")
        
        # 方法3: 重新加载当前进程的环境变量
        try:
            load_dotenv("conf/.env", override=True)
            success_count += 1
            st.info("✅ UI进程环境变量重载成功")
            total_attempts += 1
            
        except Exception as e:
            st.warning(f"⚠️ UI进程环境变量重载失败: {e}")
        
        # 判断整体成功率
        if total_attempts == 0:
            return False
        
        success_rate = success_count / total_attempts
        return success_rate >= 0.5  # 50%以上成功率认为成功
        
    except Exception as e:
        st.error(f"❌ 应用配置更改时发生异常: {e}")
        return False

def test_current_configuration(reload_env=True):
    """测试当前配置的有效性"""
    # 可选择是否重新加载环境变量（测试时可以设为 False）
    if reload_env:
        load_dotenv('conf/.env')
    
    results = {
        "ai_model": {"status": "unknown", "message": ""},
        "database": {"status": "unknown", "message": ""},
        "gitlab": {"status": "unknown", "message": ""},
        "github": {"status": "unknown", "message": ""},
        "messaging": {"status": "unknown", "message": ""}
    }
    
    try:
        # 测试AI模型配置
        llm_provider = os.environ.get('LLM_PROVIDER', '').lower().strip()
        if llm_provider:
            ai_config_valid = False
            provider_message = ""
            
            if llm_provider == 'deepseek':
                api_key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
                if api_key:
                    ai_config_valid = True
                    provider_message = "DeepSeek API密钥已配置"
                else:
                    provider_message = "DeepSeek已选择但API密钥未配置"
                    
            elif llm_provider == 'openai':
                api_key = os.environ.get('OPENAI_API_KEY', '').strip()
                if api_key:
                    ai_config_valid = True
                    provider_message = "OpenAI API密钥已配置"
                else:
                    provider_message = "OpenAI已选择但API密钥未配置"
                    
            elif llm_provider == 'zhipuai':
                api_key = os.environ.get('ZHIPUAI_API_KEY', '').strip()
                if api_key:
                    ai_config_valid = True
                    provider_message = "智谱AI API密钥已配置"
                else:
                    provider_message = "智谱AI已选择但API密钥未配置"
                    
            elif llm_provider == 'qwen':
                api_key = os.environ.get('QWEN_API_KEY', '').strip()
                if api_key:
                    ai_config_valid = True
                    provider_message = "Qwen API密钥已配置"
                else:
                    provider_message = "Qwen已选择但API密钥未配置"
                    
            elif llm_provider == 'ollama':
                api_base = os.environ.get('OLLAMA_API_BASE_URL', '').strip()
                model = os.environ.get('OLLAMA_API_MODEL', '').strip()
                if api_base and model:
                    ai_config_valid = True
                    provider_message = f"Ollama API地址已配置，模型: {model}"
                elif api_base:
                    provider_message = "Ollama API地址已配置但未指定模型"
                else:
                    provider_message = "Ollama已选择但API地址未配置"
                    
            elif llm_provider == 'jedi':
                api_key = os.environ.get('JEDI_API_KEY', '').strip()
                api_base = os.environ.get('JEDI_API_BASE_URL', '').strip()
                model = os.environ.get('JEDI_API_MODEL', '').strip()
                if api_key and api_base and model:
                    ai_config_valid = True
                    provider_message = f"Jedi API已配置，模型: {model}"
                elif api_key and api_base:
                    provider_message = "Jedi API密钥和地址已配置但未指定模型"
                elif api_key:
                    provider_message = "Jedi API密钥已配置但缺少API地址"
                else:
                    provider_message = "Jedi已选择但API密钥未配置"
            else:
                provider_message = f"不支持的AI模型提供商: {llm_provider}"
            
            if ai_config_valid:
                results["ai_model"] = {"status": "success", "message": provider_message}
            else:
                results["ai_model"] = {"status": "error", "message": provider_message}
        else:
            results["ai_model"] = {"status": "warning", "message": "未选择AI模型提供商"}
        
        # 测试数据库连接
        try:
            from biz.service.review_service import ReviewService
            review_service = ReviewService()
            # 简单测试数据库连接 - 只获取少量数据进行测试
            import time
            current_time = int(time.time())
            one_week_ago = current_time - (7 * 24 * 60 * 60)  # 一周前
            df = review_service.get_mr_review_logs(updated_at_gte=one_week_ago)
            results["database"] = {"status": "success", "message": f"数据库连接正常，最近一周有{len(df)}条记录"}
        except Exception as e:
            results["database"] = {"status": "error", "message": f"数据库连接失败: {str(e)[:100]}"}
        
        # 测试GitLab配置
        if os.environ.get('GITLAB_ENABLED', '').lower() == 'true':
            if os.environ.get('GITLAB_ACCESS_TOKEN') and os.environ.get('GITLAB_URL'):
                results["gitlab"] = {"status": "success", "message": "GitLab配置完整"}
            else:
                results["gitlab"] = {"status": "error", "message": "GitLab已启用但配置不完整"}
        else:
            results["gitlab"] = {"status": "info", "message": "GitLab功能未启用"}
        
        # 测试GitHub配置
        if os.environ.get('GITHUB_ENABLED', '').lower() == 'true':
            if os.environ.get('GITHUB_ACCESS_TOKEN'):
                results["github"] = {"status": "success", "message": "GitHub配置完整"}
            else:
                results["github"] = {"status": "error", "message": "GitHub已启用但配置不完整"}
        else:
            results["github"] = {"status": "info", "message": "GitHub功能未启用"}
        
        # 测试消息推送配置
        messaging_enabled = False
        messaging_status = []
        
        if os.environ.get('DINGTALK_ENABLED', '').lower() == 'true':
            if os.environ.get('DINGTALK_WEBHOOK_URL'):
                messaging_status.append("钉钉✅")
                messaging_enabled = True
            else:
                messaging_status.append("钉钉❌")
        
        if os.environ.get('WECOM_ENABLED', '').lower() == 'true':
            if os.environ.get('WECOM_WEBHOOK_URL'):
                messaging_status.append("企业微信✅")
                messaging_enabled = True
            else:
                messaging_status.append("企业微信❌")
        
        if os.environ.get('FEISHU_ENABLED', '').lower() == 'true':
            if os.environ.get('FEISHU_WEBHOOK_URL'):
                messaging_status.append("飞书✅")
                messaging_enabled = True
            else:
                messaging_status.append("飞书❌")
        
        if messaging_enabled:
            results["messaging"] = {"status": "success", "message": f"消息推送: {', '.join(messaging_status)}"}
        elif messaging_status:
            results["messaging"] = {"status": "warning", "message": f"消息推送配置不完整: {', '.join(messaging_status)}"}
        else:
            results["messaging"] = {"status": "info", "message": "消息推送功能未启用"}
            
    except Exception as e:
        results["error"] = {"status": "error", "message": f"配置测试异常: {e}"}
    
    return results

def display_test_results(results):
    """显示配置测试结果"""
    st.markdown("#### 🧪 配置测试结果")
    
    for component, result in results.items():
        status = result["status"]
        message = result["message"]
        
        if status == "success":
            st.success(f"✅ {component.upper()}: {message}")
        elif status == "error":
            st.error(f"❌ {component.upper()}: {message}")
        elif status == "warning":
            st.warning(f"⚠️ {component.upper()}: {message}")
        elif status == "info":
            st.info(f"ℹ️ {component.upper()}: {message}")
        else:
            st.text(f"❓ {component.upper()}: {message}")

def home_page():
    """首页"""
    # 主标题只在首页显示
    st.markdown("""
    <div class="config-card">
        <h1 style="margin: 0; text-align: center;">🤖 AI-CodeReview 代码审查仪表板</h1>
        <p style="margin: 0.5rem 0 0 0; text-align: center; font-size: 1.1rem;">
            智能代码审查系统 - 支持 SVN • GitLab • GitHub
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 系统概览卡片
    st.markdown("### 🔧 系统概览")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="overview-card">
            <h3>🔧 配置管理</h3>
            <p>系统配置一键管理</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="overview-card">
            <h3>📊 数据分析</h3>
            <p>代码审查数据洞察</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="overview-card">
            <h3>🤖 AI审查</h3>
            <p>智能代码质量分析</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="overview-card">
            <h3>🔗 多平台</h3>
            <p>SVN•GitLab•GitHub</p>
        </div>
        """, unsafe_allow_html=True)
      # 系统状态监控
    st.markdown("### ⚙️ 系统状态")
    
    try:
        from biz.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        platforms = get_platform_status(config_manager)
        env_config = config_manager.get_env_config()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**AI模型供应商**")
            llm_provider = env_config.get("LLM_PROVIDER", "未配置")
            if llm_provider and llm_provider != "未配置":
                st.markdown(f"🟢 {llm_provider}")
            else:
                st.markdown("🔴 未配置")
            
            st.markdown("**支持平台**")
            enabled_platforms = [name.upper() for name, enabled in platforms.items() if enabled]
            if enabled_platforms:
                st.markdown(f"🟢 已启用: {', '.join(enabled_platforms)}")
            else:
                st.markdown("🟡 暂无启用的平台")
        
        with col2:
            st.markdown("**配置完成度**")
            configured_count = len([v for v in env_config.values() if v and v.strip()])
            total_count = len(env_config)
            completion_rate = (configured_count / total_count * 100) if total_count > 0 else 0
            
            st.progress(completion_rate / 100)
            st.markdown(f"已配置: {configured_count}/{total_count} ({completion_rate:.1f}%)")
    
    except Exception as e:
        st.error(f"获取系统状态失败: {e}")
        st.info("请检查配置文件是否正确设置")
    
    # 快速开始指南
    st.markdown("### 🚀 快速开始")
    with st.expander("📖 首次使用指南", expanded=False):
        st.markdown("""
        #### 第一步：配置AI模型
        1. 点击左侧"⚙️ 配置管理"
        2. 选择AI模型供应商（OpenAI、DeepSeek、智谱AI等）
        3. 输入对应的API Key
        
        #### 第二步：启用代码平台
        1. 在"平台开关"中启用需要的平台
        2. 配置对应的访问令牌和URL
        
        #### 第三步：查看分析数据
        1. 点击左侧"📊 数据分析"
        2. 查看代码审查统计和详细记录
        
        #### 获取帮助
        - 查看左侧"📖 使用帮助"获取详细说明
        - 检查系统状态确保配置正确
        """)
    
    # 系统信息
    st.markdown("### ℹ️ 系统信息")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown("**支持的功能**")
        st.markdown("""
        - ✅ 多平台代码审查（SVN/GitLab/GitHub）
        - ✅ AI智能代码分析
        - ✅ 实时数据统计和可视化
        - ✅ 自定义审查规则
        - ✅ 多种AI模型支持        """)
    
    with info_col2:
        st.markdown("**当前配置信息**")
        try:
            from biz.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            env_config = config_manager.get_env_config()
            
            st.markdown(f"- **AI模型**: {env_config.get('LLM_PROVIDER', '未配置')}")
            st.markdown(f"- **服务端口**: {env_config.get('SERVER_PORT', '8000')}")
            st.markdown(f"- **日志级别**: {env_config.get('LOG_LEVEL', 'DEBUG')}")
            st.markdown(f"- **队列驱动**: {env_config.get('QUEUE_DRIVER', 'sync')}")
        except:
            st.markdown("- 配置信息加载中...")

def data_analysis_page():
    """数据分析页面 - 优化版本"""
    # 页面标题
    st.markdown("""
    <div class="config-card">
        <h2 style="margin: 0; text-align: center;">📊 代码审查数据分析</h2>
        <p style="margin: 0.5rem 0 0 0; text-align: center; font-size: 1.1rem;">分析代码审查数据，洞察代码质量趋势</p>
    </div>
    """, unsafe_allow_html=True)
      # 获取平台开关配置
    from biz.utils.config_manager import ConfigManager
    config_manager = ConfigManager()
    try:
        platforms = get_platform_status(config_manager)
        
        # 检查是否有启用的平台
        if not any(platforms.values()):
            st.warning("⚠️ 所有代码托管平台都已禁用，请在配置管理中启用至少一个平台。")
            with st.expander("💡 如何启用平台？"):
                st.markdown("""
                1. 点击侧边栏的 "⚙️ 配置管理"
                2. 在 "平台开关配置" 部分启用需要的平台
                3. 保存配置并刷新页面
                """)
            return
        
        # 使用缓存获取审查统计数据
        with st.spinner("📊 正在加载统计数据..."):
            review_stats = get_review_stats(platforms)
        
        # 显示整体数据概览
        _display_data_overview(review_stats, platforms)
        
        # 分隔线
        st.markdown("---")
        
        # 数据分析主体
        _display_detailed_analysis(review_stats, platforms)
        
    except Exception as e:
        st.error(f"❌ 加载数据分析页面失败: {e}")
        with st.expander("🔧 故障排除"):
            st.markdown("""
            **可能的原因：**
            1. 配置文件损坏或缺失
            2. 数据库连接问题
            3. 权限不足
            
            **解决方案：**
            1. 检查配置管理页面的配置项
            2. 重启应用程序
            3. 查看日志文件获取详细错误信息
            """)

def _display_data_overview(review_stats, platforms):
    """显示数据概览"""
    st.markdown("### 📈 数据概览")
    
    # 计算总数
    total_reviews = sum([
        review_stats.get('mr_count', 0),
        review_stats.get('push_count', 0), 
        review_stats.get('svn_count', 0),
        review_stats.get('github_count', 0)
    ])
    
    # 概览指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 总审查数",
            value=f"{total_reviews:,}",
            help="所有平台的审查记录总数"
        )
    
    with col2:
        active_platforms = sum(platforms.values())
        st.metric(
            label="🔗 活跃平台", 
            value=f"{active_platforms}/3",
            help="已启用的代码托管平台数量"
        )
    
    with col3:
        # 计算最活跃的平台
        platform_counts = {
            'GitLab': review_stats.get('mr_count', 0) + review_stats.get('push_count', 0),
            'SVN': review_stats.get('svn_count', 0),
            'GitHub': review_stats.get('github_count', 0)
        }
        most_active = max(platform_counts, key=platform_counts.get) if total_reviews > 0 else "无"
        st.metric(
            label="🏆 主力平台",
            value=most_active,
            help="审查记录最多的平台"
        )
    
    with col4:
        # 今日新增（模拟数据，实际需要从数据库查询）
        st.metric(
            label="📅 近7天",
            value="暂无",
            help="最近7天的审查记录数"
        )

def _display_detailed_analysis(review_stats, platforms):
    """显示详细数据分析"""
    st.markdown("### 🔍 详细数据分析")
    
    # 根据平台开关动态生成可用的审查类型
    available_types = []
    type_labels = {}
    
    # 根据实际数据显示可用类型
    if platforms.get('gitlab') and review_stats.get('mr_count', 0) > 0:
        available_types.append('mr')
        type_labels['mr'] = f"🔀 GitLab MR ({review_stats['mr_count']} 条)"
    
    if platforms.get('gitlab') and review_stats.get('push_count', 0) > 0:
        available_types.append('push')
        type_labels['push'] = f"📤 GitLab Push ({review_stats['push_count']} 条)"
    
    if platforms.get('svn') and review_stats.get('svn_count', 0) > 0:
        available_types.append('svn')
        type_labels['svn'] = f"📂 SVN 提交 ({review_stats['svn_count']} 条)"
    
    if platforms.get('github') and review_stats.get('github_count', 0) > 0:
        available_types.append('github')
        type_labels['github'] = f"🐙 GitHub ({review_stats['github_count']} 条)"
    
    # 如果没有数据但平台启用了，显示暂无数据提示
    if not available_types:
        enabled_platforms = [k for k, v in platforms.items() if v]
        if enabled_platforms:
            st.info(f"📊 已启用的平台 ({', '.join(enabled_platforms)}) 暂无审查数据")
            st.markdown("""
            **💡 可能的原因：**
            - 系统刚配置完成，还没有审查记录
            - 审查功能尚未触发
            - 数据同步延迟
            
            **建议操作：**
            - 检查Webhook配置是否正确
            - 查看应用日志确认审查功能是否正常工作
            - 手动触发一次代码提交测试
            """)
        return
    
    # 审查类型选择
    col_select, col_refresh = st.columns([3, 1])
    
    with col_select:
        review_type = st.selectbox(
            "选择审查类型",
            available_types,
            format_func=lambda x: type_labels.get(x, x),
            help="选择要分析的代码审查类型"
        )
    
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)  # 对齐按钮
        if st.button("🔄 刷新数据", key="refresh_data_btn", help="刷新页面数据"):
            st.rerun()
    
    # 高级筛选选项
    with st.expander("🔍 高级筛选选项", expanded=False):
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # 作者筛选 - 优化加载性能
            with st.spinner("加载作者列表..."):
                available_authors = get_available_authors([review_type])
            
            selected_authors = st.multiselect(
                "筛选作者", 
                available_authors,
                help="选择要分析的作者，留空表示包含所有作者"
            )
            
            # 项目筛选
            with st.spinner("加载项目列表..."):
                available_projects = get_available_projects([review_type])
            
            selected_projects = st.multiselect(
                "筛选项目",
                available_projects,
                help="选择要分析的项目，留空表示包含所有项目"
            )
        
        with filter_col2:
            # 时间范围筛选 - 提供预设选项
            st.markdown("**时间范围**")
            time_preset = st.radio(
                "快速选择",
                ["自定义", "最近7天", "最近30天", "最近90天"],
                horizontal=True,
                help="选择分析的时间范围"
            )
            
            if time_preset == "自定义":
                date_range = st.date_input(
                    "自定义时间范围",
                    value=(),
                    help="选择自定义时间范围"
                )
            else:
                # 计算预设时间范围
                from datetime import datetime, timedelta
                today = datetime.now().date()
                
                if time_preset == "最近7天":
                    date_range = (today - timedelta(days=7), today)
                elif time_preset == "最近30天":
                    date_range = (today - timedelta(days=30), today)
                elif time_preset == "最近90天":
                    date_range = (today - timedelta(days=90), today)
                
                st.info(f"时间范围: {date_range[0]} 到 {date_range[1]}")
            
            # 评分范围筛选
            score_range = st.slider(
                "评分范围",
                min_value=0,
                max_value=100,
                value=(0, 100),
                help="选择评分范围"
            )
      # 显示选中类型的详细数据
    if review_type:
        # 处理时间范围
        processed_date_range = None
        if hasattr(date_range, '__len__') and len(date_range) == 2:
            processed_date_range = date_range
        elif hasattr(date_range, '__len__') and len(date_range) == 1:
            processed_date_range = (date_range[0], date_range[0])
        
        # 显示版本追踪数据
        with st.spinner(f"📊 正在加载 {review_type.upper()} 数据..."):
            display_version_tracking_data(
                review_type=review_type,
                authors=selected_authors if selected_authors else None,
                projects=selected_projects if selected_projects else None,
                date_range=processed_date_range,
                score_range=score_range            )

def env_management_page():
    """配置管理页面"""
    import json
    import datetime
    from dotenv import load_dotenv
    import pandas as pd
    
    # 确保在函数作用域内导入 ConfigManager
    from biz.utils.config_manager import ConfigManager
    
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; margin-bottom: 2rem; color: white; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 2.2rem;">⚙️ 系统配置管理</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;">集中管理所有系统配置，让部署更简单</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # 安全地创建 ConfigManager 实例，添加错误处理
        config_manager = ConfigManager()
    except Exception as e:
        st.error(f"❌ 初始化配置管理器失败: {e}")
        st.info("请检查以下问题：\n1. 确保 biz.utils.config_manager 模块存在\n2. 确保 ConfigManager 类正确定义\n3. 检查文件权限和路径")
        return
    # 创建选项卡
    tab1, tab2, tab3 = st.tabs(["🎛️ 系统配置", "📋 配置总览", "🔧 配置模板"])
    
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
                    ["deepseek", "openai", "zhipuai", "qwen", "jedi", "ollama"],
                    index=["deepseek", "openai", "zhipuai", "qwen", "jedi", "ollama"].index(env_config.get("LLM_PROVIDER", "deepseek"))
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
                    
                    st.markdown("**智谱AI 配置**")
                    zhipuai_key = st.text_input("智谱AI API Key", value=env_config.get("ZHIPUAI_API_KEY", ""), type="password")
                    zhipuai_model = st.text_input("智谱AI Model", value=env_config.get("ZHIPUAI_API_MODEL", "GLM-4-Flash"))
                
                with col_ai2:
                    st.markdown("**Jedi 配置**")
                    jedi_key = st.text_input("Jedi API Key", value=env_config.get("JEDI_API_KEY", ""), type="password")
                    jedi_base = st.text_input("Jedi API Base", value=env_config.get("JEDI_API_BASE_URL", "https://jedi-jp-prd-ai-tools.bekko.com:30001/chat_completion_api"))
                    jedi_model = st.text_input("Jedi Model", value=env_config.get("JEDI_API_MODEL", "official-deepseek-r1"))
                    
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
                                              ["async", "memory"],
                                              index=0 if env_config.get("QUEUE_DRIVER", "async") == "async" else 1)
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
                    svn_check_cron = st.text_input("SVN检查时间(Cron)", value=env_config.get("SVN_CHECK_CRONTAB", "*/30 * * * *"))
                    svn_check_limit = st.number_input("每次检查最大提交数", 
                                                    min_value=1, max_value=1000, 
                                                    value=int(env_config.get("SVN_CHECK_LIMIT", "100") or "100"))
                
                with col8:
                    st.info("💡 SVN功能的启用/禁用在上面的'平台开关配置'中设置")
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
                    extra_webhook_url = st.text_input("额外Webhook URL", value=env_config.get("EXTRA_WEBHOOK_URL", ""), type="password")
            
            # 保存按钮
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
                    # SVN配置 - 使用平台开关作为主控制
                    "SVN_CHECK_ENABLED": "1" if svn_enabled else "0",
                    "SVN_CHECK_CRONTAB": svn_check_cron,
                    "SVN_CHECK_LIMIT": str(svn_check_limit),
                    "SVN_REVIEW_ENABLED": "1" if svn_enabled else "0",  # 跟随主开关
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
                    
                    # Jedi配置
                    "JEDI_API_KEY": jedi_key,
                    "JEDI_API_BASE_URL": jedi_base,
                    "JEDI_API_MODEL": jedi_model,
                    
                    # Ollama配置
                    "OLLAMA_API_BASE_URL": ollama_base,
                    "OLLAMA_API_MODEL": ollama_model
                })
                
                try:
                    if config_manager.save_env_config(new_config):
                        st.success("✅ 系统配置已成功保存！")
                        
                        # 尝试立即生效配置
                        with st.spinner("🔄 正在应用配置更改..."):
                            reload_success = apply_config_changes()
                            
                        if reload_success:
                            st.success("🎉 配置已立即生效！无需重启服务。")
                            st.balloons()
                        else:
                            st.warning("⚠️ 配置已保存，但部分更改可能需要重启服务才能完全生效。")
                            st.info("💡 建议手动重启相关服务以确保所有更改生效。")
                        
                        # 重新加载当前页面的环境变量
                        load_dotenv("conf/.env", override=True)
                        
                        # 短暂延迟后刷新页面
                        import time
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ 保存配置失败，请检查文件权限。")
                except Exception as e:
                    st.error(f"❌ 保存配置失败: {e}")
        
        # 添加配置测试按钮 - 移出form范围
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🧪 测试当前配置", key="env_mgmt_test_config_btn", help="测试当前配置的有效性"):
                with st.spinner("正在测试配置..."):
                    try:
                        test_results = test_current_configuration()
                        display_test_results(test_results)
                    except Exception as e:
                        st.error(f"配置测试失败: {e}")
        
        with col2:
            if st.button("🔄 立即重载配置", key="env_mgmt_reload_config_btn", help="立即重载当前配置到系统"):
                with st.spinner("正在重载配置..."):
                    try:
                        reload_success = apply_config_changes()
                        if reload_success:
                            st.success("✅ 配置重载成功！")
                        else:
                            st.warning("⚠️ 配置重载部分成功，建议检查服务状态")
                    except Exception as e:
                        st.error(f"配置重载失败: {e}")
        
        with col3:
            if st.button("📊 检查服务状态", key="env_mgmt_check_status_btn", help="检查API和后台服务的运行状态"):
                with st.spinner("正在检查服务状态..."):
                    try:
                        service_status = check_service_status()
                        display_service_status(service_status)
                    except Exception as e:
                        st.error(f"状态检查失败: {e}")
    
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
                                   "JEDI_API_KEY", "JEDI_API_BASE_URL", "JEDI_API_MODEL",
                                   "OLLAMA_API_BASE_URL", "OLLAMA_API_MODEL",
                                   "REVIEW_STYLE", "REVIEW_MAX_TOKENS", "SUPPORTED_EXTENSIONS"],
                    "🔀 平台开关": ["SVN_CHECK_ENABLED", "GITLAB_ENABLED", "GITHUB_ENABLED"],
                    "📋 版本追踪配置": ["VERSION_TRACKING_ENABLED", "REUSE_PREVIOUS_REVIEW_RESULT", "VERSION_TRACKING_RETENTION_DAYS"],
                    "🏠 系统配置": ["SERVER_PORT", "TZ", "LOG_LEVEL", "LOG_FILE", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT", "QUEUE_DRIVER"],
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
                with col_stat2:
                    st.metric("已配置项", configured_items)
                with col_stat3:
                    completion_rate = (configured_items / total_items * 100) if total_items > 0 else 0
                    st.metric("配置完成度", f"{completion_rate:.1f}%")
                    
            else:
                st.warning("⚠️ 无法读取环境变量配置")
                
        except Exception as e:
            st.error(f"❌ 读取配置失败: {e}")
    
    with tab3:
        st.markdown("### 🔧 配置模板管理")
        st.markdown("🚀 **快速部署配置模板**，根据不同环境选择最佳配置组合。")
        
        col_template1, col_template2 = st.columns(2)
        
        with col_template1:
            st.markdown("#### 🔧 环境模板")
            
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
                
                if st.button(f"应用{selected_template}模板", key="apply_template", help=f"将当前配置替换为{selected_template}模板配置"):
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
            if st.button("🔄 重置为默认配置", key="reset_config", help="将所有配置重置为系统默认值"):
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
            if st.button("📥 导出当前配置", key="export_config", help="将当前配置导出为环境变量文件"):
                try:
                    current_config = config_manager.get_env_config()
                    if current_config:
                        # 创建导出内容
                        export_content = "# AI代码审查系统配置文件\n"
                        export_content += f"# 导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        
                        # 导入ConfigManager来安全处理环境变量
                        from biz.utils.config_manager import ConfigManager
                        
                        for key, value in current_config.items():
                            escaped_value = ConfigManager._escape_env_value(value)
                            export_content += f"{key}={escaped_value}\n"
                        
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

def check_service_status():
    """检查各个服务的运行状态（单服务架构）"""
    status = {
        "api": {"running": False, "message": ""},
        "ui": {"running": True, "message": "当前UI服务正在运行"},
        "database": {"running": False, "message": ""},
        "config": {"running": False, "message": ""}
    }
    
    try:
        # 检查API服务
        api_port = os.environ.get('API_PORT', '5001')
        try:
            response = requests.get(f"http://localhost:{api_port}/health", timeout=3)
            if response.status_code == 200:
                status["api"] = {"running": True, "message": f"API服务运行正常 (端口{api_port})"}
            else:
                status["api"] = {"running": False, "message": f"API服务响应异常 (状态码: {response.status_code})"}
        except requests.exceptions.ConnectionError:
            status["api"] = {"running": False, "message": f"API服务连接失败 (端口{api_port})"}
        except Exception as e:
            status["api"] = {"running": False, "message": f"API服务检查异常: {str(e)[:50]}"}
        
        # 检查数据库连接
        try:
            from biz.service.review_service import ReviewService
            review_service = ReviewService()
            # 简单的数据库连接测试
            review_service.get_mr_review_logs()
            status["database"] = {"running": True, "message": "数据库连接正常"}
        except Exception as e:
            status["database"] = {"running": False, "message": f"数据库连接失败: {str(e)[:50]}"}
        
        # 检查配置管理
        try:
            from biz.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.get_env_config()
            if config:
                status["config"] = {"running": True, "message": f"配置加载正常 ({len(config)}项)"}
            else:
                status["config"] = {"running": False, "message": "配置为空"}
        except Exception as e:
            status["config"] = {"running": False, "message": f"配置检查异常: {str(e)[:50]}"}
    
    except Exception as e:
        # 如果整个检查过程出现异常，记录错误
        for key in status:
            if key != "ui":  # UI肯定是运行的，因为代码在执行
                status[key] = {"running": False, "message": f"检查异常: {str(e)[:30]}"}
    
    return status


def display_service_status(status):
    """显示服务状态"""
    st.markdown("#### 📊 服务运行状态")
    
    for service, info in status.items():
        if service == "error":
            st.error(f"❌ {info['message']}")
            continue
            
        is_running = info["running"]
        message = info["message"]
        
        if is_running:
            st.success(f"🟢 {service.upper()}: {message}")
        else:
            st.error(f"🔴 {service.upper()}: {message}")
    
    # 添加服务管理提示
    st.markdown("---")
    st.markdown("##### 💡 服务管理提示")
    st.info("""
    - **API服务**: 处理webhook请求和代码审查，集成后台任务处理
    - **UI服务**: 当前仪表板界面 (正在运行)
    - **数据库**: SQLite数据库连接状态
    - **配置**: 系统配置文件加载状态
    
    **单服务架构**: API、UI和后台任务已合并在一个服务中运行
    """)
