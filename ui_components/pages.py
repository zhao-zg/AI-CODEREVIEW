"""
页面组件模块
"""

import streamlit as st
import requests
import os
import json
import datetime
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
            # 使用API_URL配置
            api_url_base = os.environ.get('API_URL', 'http://localhost:5001')
            api_url = f"{api_url_base}/reload-config"
            
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

# 支持的 AI 供应商（与「🤖 AI模型」标签页中的顺序保持一致）
LLM_PROVIDERS = ["deepseek", "openai", "zhipuai", "qwen", "jedi", "ollama"]

# 配置总览的分类定义
CONFIG_CATEGORIES = {
    "🤖 AI模型": ["LLM_PROVIDER", "DEEPSEEK_API_KEY", "DEEPSEEK_API_BASE_URL", "DEEPSEEK_API_MODEL",
                "OPENAI_API_KEY", "OPENAI_API_BASE_URL", "OPENAI_API_MODEL",
                "ZHIPUAI_API_KEY", "ZHIPUAI_API_MODEL",
                "QWEN_API_KEY", "QWEN_API_BASE_URL", "QWEN_API_MODEL",
                "JEDI_API_KEY", "JEDI_API_BASE_URL", "JEDI_API_MODEL",
                "OLLAMA_API_BASE_URL", "OLLAMA_API_MODEL"],
    "🎯 审查设置": ["REVIEW_MAX_TOKENS", "SUPPORTED_EXTENSIONS", "EXCLUDE_PATTERNS", "SVN_DIFF_CONTEXT_LINES",
                "AGENTIC_REVIEW_ENABLED", "AGENTIC_REVIEW_MAX_TOOL_ROUNDS",
                "VERSION_TRACKING_ENABLED", "REUSE_PREVIOUS_REVIEW_RESULT", "VERSION_TRACKING_RETENTION_DAYS"],
    "🔀 平台开关": ["SVN_CHECK_ENABLED", "GITLAB_ENABLED", "GITHUB_ENABLED"],
    "🔗 GitLab": ["GITLAB_URL", "GITLAB_ACCESS_TOKEN", "PUSH_REVIEW_ENABLED",
                "MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED"],
    "🐙 GitHub": ["GITHUB_URL", "GITHUB_ACCESS_TOKEN"],
    "📂 SVN": ["SVN_REVIEW_ENABLED", "SVN_CHECK_CRONTAB", "SVN_CHECK_LIMIT", "SVN_REPOSITORIES",
             "USE_ENHANCED_MERGE_DETECTION", "MERGE_DETECTION_THRESHOLD"],
    "🔔 通知推送": ["NOTIFICATION_MODE", "DINGTALK_ENABLED", "DINGTALK_WEBHOOK_URL",
                "WECOM_ENABLED", "WECOM_WEBHOOK_URL", "FEISHU_ENABLED", "FEISHU_WEBHOOK_URL",
                "EXTRA_WEBHOOK_ENABLED", "EXTRA_WEBHOOK_URL"],
    "🖥️ 系统运行": ["API_PORT", "API_URL", "UI_PORT", "UI_URL", "TZ", "LOG_LEVEL", "LOG_FILE",
                 "LOG_MAX_BYTES", "LOG_BACKUP_COUNT", "QUEUE_DRIVER", "REDIS_HOST", "REDIS_PORT",
                 "REPORT_CRONTAB_EXPRESSION"],
    "👤 Dashboard": ["DASHBOARD_USER", "DASHBOARD_PASSWORD"],
}

# 需要在界面上打码的配置项关键字
SENSITIVE_KEY_HINTS = ("PASSWORD", "TOKEN", "KEY", "SECRET", "WEBHOOK")

# 环境快速配置模板（只覆盖列出的配置项）
ENV_TEMPLATES = {
    "🔧 开发环境": {
        "LLM_PROVIDER": "deepseek",
        "LOG_LEVEL": "DEBUG",
        "SVN_CHECK_ENABLED": "1",
        "GITLAB_ENABLED": "1",
        "GITHUB_ENABLED": "1",
        "DINGTALK_ENABLED": "0",
        "WECOM_ENABLED": "0",
        "FEISHU_ENABLED": "0",
    },
    "🚀 生产环境": {
        "LLM_PROVIDER": "openai",
        "LOG_LEVEL": "INFO",
        "SVN_CHECK_ENABLED": "1",
        "GITLAB_ENABLED": "1",
        "GITHUB_ENABLED": "1",
        "DINGTALK_ENABLED": "1",
        "WECOM_ENABLED": "1",
        "FEISHU_ENABLED": "1",
    },
    "🧪 测试环境": {
        "LLM_PROVIDER": "ollama",
        "LOG_LEVEL": "DEBUG",
        "SVN_CHECK_ENABLED": "1",
        "GITLAB_ENABLED": "1",
        "GITHUB_ENABLED": "0",
        "DINGTALK_ENABLED": "0",
        "WECOM_ENABLED": "0",
        "FEISHU_ENABLED": "0",
    },
}


def _is_sensitive_key(key):
    """判断配置项是否为敏感信息"""
    return any(hint in key.upper() for hint in SENSITIVE_KEY_HINTS)


def _env_int(env_config, key, default):
    """安全地把配置项解析为整数，解析失败时回退默认值，避免脏配置导致配置页无法打开"""
    try:
        return int(str(env_config.get(key, "")).strip() or default)
    except (TypeError, ValueError):
        return default


def _env_float(env_config, key, default):
    """安全地把配置项解析为浮点数，解析失败时回退默认值"""
    try:
        return float(str(env_config.get(key, "")).strip() or default)
    except (TypeError, ValueError):
        return default


def _mask_value(value):
    """对敏感配置值打码，仅保留末尾4位便于核对"""
    if not value:
        return "未设置"
    return "••••••••" + value[-4:] if len(value) > 4 else "••••••••"


def _render_config_summary(env_config):
    """渲染配置页顶部的状态摘要"""
    enabled_platforms = [
        name for key, name in (
            ("SVN_CHECK_ENABLED", "SVN"),
            ("GITLAB_ENABLED", "GitLab"),
            ("GITHUB_ENABLED", "GitHub"),
        ) if env_config.get(key, "0") == "1"
    ]
    enabled_channels = [
        name for key, name in (
            ("DINGTALK_ENABLED", "钉钉"),
            ("WECOM_ENABLED", "企业微信"),
            ("FEISHU_ENABLED", "飞书"),
            ("EXTRA_WEBHOOK_ENABLED", "自定义"),
        ) if env_config.get(key, "0") == "1"
    ]
    configured_count = len([v for v in env_config.values() if v and str(v).strip()])
    total_count = len(env_config)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("当前AI供应商", env_config.get("LLM_PROVIDER") or "未配置")
    col2.metric("已启用平台", "、".join(enabled_platforms) if enabled_platforms else "无")
    col3.metric("通知渠道", "、".join(enabled_channels) if enabled_channels else "无")
    col4.metric("配置完成度", f"{configured_count}/{total_count}" if total_count else "0/0")


def _save_env_config(config_manager, updates):
    """保存环境配置：与磁盘上的现有配置合并后整体写回

    ConfigManager.save_env_config 会整体重写 conf/.env，若只传入表单字段，
    界面上没有覆盖到的配置项（如 SVN_CHECK_CRONTAB 等）会被静默丢弃，因此先合并。
    """
    merged = config_manager.get_env_config() or {}
    merged.update({key: ("" if value is None else str(value)) for key, value in updates.items()})
    return config_manager.save_env_config(merged)


def env_management_page():
    """配置管理页面"""
    import pandas as pd

    st.markdown("""
    <div class="config-card">
        <h2 style="margin: 0; text-align: center;">⚙️ 系统配置管理</h2>
        <p style="margin: 0.5rem 0 0 0; text-align: center; font-size: 1.05rem;">按模块分组管理系统配置，保存后自动重载生效</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config() or {}
    except Exception as e:
        st.error(f"❌ 初始化配置管理器失败: {e}")
        st.caption("请确认 conf/ 目录存在，且 conf/.env、conf_templates/.env.dist 可读写。")
        return

    _render_config_summary(env_config)
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🎛️ 系统配置", "📋 配置总览", "🔧 配置模板"])

    with tab1:
        st.caption("配置按模块分组，在下方标签页中填写，完成后点击底部「💾 保存系统配置」统一保存并生效。")

        # 配置编辑表单 - 按模块分组，避免单页长滚动
        # 注意：下方各 with 块的书写顺序与标签展示顺序不一致（Streamlit 按 tab 对象归属渲染，不按代码顺序）
        with st.form("env_config_form"):
            t_basic, t_review, t_ai, t_repo, t_notify, t_system, t_prompt = st.tabs([
                "🚀 基础", "🎯 审查设置", "🤖 AI模型", "🏛️ 代码平台",
                "🔔 通知推送", "🖥️ 系统运行", "📝 Prompt模板",
            ])

            # ------------------------------ 基础 ------------------------------
            with t_basic:
                with st.container(border=True):
                    st.markdown("**🧠 AI 供应商**")
                    col_basic1, col_basic2 = st.columns(2)
                    with col_basic1:
                        current_provider = env_config.get("LLM_PROVIDER", "deepseek")
                        llm_provider = st.selectbox(
                            "使用的AI供应商",
                            LLM_PROVIDERS,
                            index=LLM_PROVIDERS.index(current_provider) if current_provider in LLM_PROVIDERS else 0,
                            help="所选供应商的 API Key / 地址 / 模型在「🤖 AI模型」标签页中填写"
                        )
                    with col_basic2:
                        timezone = st.text_input("时区", value=env_config.get("TZ", "Asia/Shanghai"))

                with st.container(border=True):
                    st.markdown("**🔀 平台开关**")
                    st.caption("关闭的平台不参与代码审查，其数据也不会出现在数据分析页面；详细参数在「🏛️ 代码平台」标签页配置。")
                    col_platform1, col_platform2, col_platform3 = st.columns(3)
                    with col_platform1:
                        svn_enabled = st.checkbox("启用 SVN", value=env_config.get("SVN_CHECK_ENABLED", "0") == "1")
                    with col_platform2:
                        gitlab_enabled = st.checkbox("启用 GitLab", value=env_config.get("GITLAB_ENABLED", "1") == "1")
                    with col_platform3:
                        github_enabled = st.checkbox("启用 GitHub", value=env_config.get("GITHUB_ENABLED", "1") == "1")

                with st.container(border=True):
                    st.markdown("**🌐 服务地址**")
                    col_addr1, col_addr2 = st.columns(2)
                    with col_addr1:
                        api_port = st.text_input("API 端口", value=env_config.get("API_PORT", "5001"),
                                                 help="容器部署时可通过端口映射修改")
                        api_url = st.text_input("API 外部地址", value=env_config.get("API_URL", "http://localhost:5001"),
                                                help="用于内部API调用，如: http://yourserver.com:5001")
                    with col_addr2:
                        ui_port = st.text_input("UI 端口", value=env_config.get("UI_PORT", "5002"),
                                                help="容器部署时可通过端口映射修改")
                        ui_url = st.text_input("UI 外部地址", value=env_config.get("UI_URL", "http://localhost:5002"),
                                               help="用于推送消息中的详情页链接，如: http://yourserver.com:5002")

                with st.container(border=True):
                    st.markdown("**👤 管理员账号**")
                    col_user1, col_user2 = st.columns(2)
                    with col_user1:
                        dashboard_user = st.text_input("Dashboard 用户名", value=env_config.get("DASHBOARD_USER", "admin"))
                    with col_user2:
                        dashboard_password = st.text_input("Dashboard 密码", value=env_config.get("DASHBOARD_PASSWORD", "admin"),
                                                           type="password")

            # ---------------------------- 审查设置 ----------------------------
            with t_review:
                with st.container(border=True):
                    st.markdown("**🎯 审查范围与限制**")
                    col_scope1, col_scope2 = st.columns(2)
                    with col_scope1:
                        supported_extensions = st.text_input(
                            "参与审查的文件扩展名",
                            value=env_config.get("SUPPORTED_EXTENSIONS", ".py,.js,.java,.cpp,.c,.h"),
                            help="逗号分隔，例如：.py,.java,.ts"
                        )
                        review_max_tokens = st.number_input(
                            "单次审查最大 Token 数",
                            min_value=1000, max_value=100000, step=1000,
                            value=_env_int(env_config, "REVIEW_MAX_TOKENS", 10000),
                            help="超出后会自动分批审查。需不超过所选模型的上下文窗口，否则会被模型截断"
                        )
                    with col_scope2:
                        exclude_patterns = st.text_input(
                            "排除的文件路径模式",
                            value=env_config.get("EXCLUDE_PATTERNS", ""),
                            help="逗号分隔，支持通配符 *。例如：*.pb.go,vendor/*,node_modules/*,*.min.js"
                        )
                        svn_diff_context_lines = st.number_input(
                            "SVN diff 上下文行数",
                            min_value=0, max_value=100,
                            value=_env_int(env_config, "SVN_DIFF_CONTEXT_LINES", 10),
                            help="对应 svn diff -U 参数，调大可让AI看到更完整的函数体"
                        )

                with st.container(border=True):
                    st.markdown("**🤖 Agentic 审查（工具调用式审查）**")
                    st.caption("开启后AI可在审查过程中主动读取完整文件、检索代码库，补足只看 diff 缺失的上下文。"
                               "openai/deepseek/qwen/zhipuai 走原生 function calling，ollama/jedi 自动降级为文本协议模拟。目前仅 SVN 审查链路接入。")
                    col_agentic1, col_agentic2 = st.columns(2)
                    with col_agentic1:
                        agentic_review_enabled = st.checkbox(
                            "启用 Agentic 审查",
                            value=env_config.get("AGENTIC_REVIEW_ENABLED", "0") == "1"
                        )
                    with col_agentic2:
                        agentic_max_tool_rounds = st.number_input(
                            "最大工具调用轮数",
                            min_value=1, max_value=20,
                            value=_env_int(env_config, "AGENTIC_REVIEW_MAX_TOOL_ROUNDS", 5),
                            help="防止工具调用失控导致费用与耗时飙升，达到上限后强制要求AI直接给出结论"
                        )

                with st.container(border=True):
                    st.markdown("**♻️ 结果复用与版本追踪**")
                    col_version1, col_version2, col_version3 = st.columns(3)
                    with col_version1:
                        version_tracking_enabled = st.checkbox(
                            "启用版本追踪",
                            value=env_config.get("VERSION_TRACKING_ENABLED", "1") == "1"
                        )
                    with col_version2:
                        reuse_previous_review = st.checkbox(
                            "复用历史审查结果",
                            value=env_config.get("REUSE_PREVIOUS_REVIEW_RESULT", "1") == "1",
                            help="内容未变化时直接复用上次审查结果，避免重复调用AI"
                        )
                    with col_version3:
                        retention_days = st.number_input(
                            "版本记录保留天数",
                            min_value=1, max_value=365,
                            value=_env_int(env_config, "VERSION_TRACKING_RETENTION_DAYS", 30)
                        )

            # ----------------------------- AI模型 -----------------------------
            with t_ai:
                st.caption(f"各供应商的配置互相独立且都会保留，切换供应商无需重填。当前生效：**{env_config.get('LLM_PROVIDER', '未配置')}**")

                col_ai1, col_ai2, col_ai3 = st.columns(3)

                with col_ai1:
                    with st.container(border=True):
                        st.markdown("**DeepSeek**")
                        deepseek_key = st.text_input("DeepSeek API Key", value=env_config.get("DEEPSEEK_API_KEY", ""), type="password")
                        deepseek_base = st.text_input("DeepSeek API Base", value=env_config.get("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com"))
                        deepseek_model = st.text_input("DeepSeek 模型", value=env_config.get("DEEPSEEK_API_MODEL", "deepseek-chat"))

                with col_ai2:
                    with st.container(border=True):
                        st.markdown("**OpenAI（兼容网关）**")
                        openai_key = st.text_input("OpenAI API Key", value=env_config.get("OPENAI_API_KEY", ""), type="password")
                        openai_base = st.text_input("OpenAI API Base", value=env_config.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1"))
                        openai_model = st.text_input("OpenAI 模型", value=env_config.get("OPENAI_API_MODEL", "gpt-4o-mini"))

                with col_ai3:
                    with st.container(border=True):
                        st.markdown("**智谱AI**")
                        zhipuai_key = st.text_input("智谱AI API Key", value=env_config.get("ZHIPUAI_API_KEY", ""), type="password")
                        st.caption("使用官方默认地址，无需配置 API Base")
                        zhipuai_model = st.text_input("智谱AI 模型", value=env_config.get("ZHIPUAI_API_MODEL", "GLM-4-Flash"))

                col_ai4, col_ai5, col_ai6 = st.columns(3)

                with col_ai4:
                    with st.container(border=True):
                        st.markdown("**通义千问 Qwen**")
                        qwen_key = st.text_input("Qwen API Key", value=env_config.get("QWEN_API_KEY", ""), type="password")
                        qwen_base = st.text_input("Qwen API Base", value=env_config.get("QWEN_API_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
                        qwen_model = st.text_input("Qwen 模型", value=env_config.get("QWEN_API_MODEL", "qwen-coder-plus"))

                with col_ai5:
                    with st.container(border=True):
                        st.markdown("**Jedi**")
                        jedi_key = st.text_input("Jedi API Key", value=env_config.get("JEDI_API_KEY", ""), type="password")
                        jedi_base = st.text_input("Jedi API Base", value=env_config.get("JEDI_API_BASE_URL", "https://jedi-jp-prd-ai-tools.bekko.com:30001/chat_completion_api"))
                        jedi_model = st.text_input("Jedi 模型", value=env_config.get("JEDI_API_MODEL", "official-deepseek-r1"))

                with col_ai6:
                    with st.container(border=True):
                        st.markdown("**Ollama（本地）**")
                        st.caption("本地部署，无需 API Key")
                        ollama_base = st.text_input("Ollama API Base", value=env_config.get("OLLAMA_API_BASE_URL", "http://host.docker.internal:11434"))
                        ollama_model = st.text_input("Ollama 模型", value=env_config.get("OLLAMA_API_MODEL", "deepseek-r1:latest"))
            
            # ---------------------------- 系统运行 ----------------------------
            with t_system:
                with st.container(border=True):
                    st.markdown("**📜 日志**")
                    col_log1, col_log2 = st.columns(2)
                    with col_log1:
                        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
                        current_log_level = env_config.get("LOG_LEVEL", "DEBUG")
                        log_level = st.selectbox(
                            "日志级别", log_levels,
                            index=log_levels.index(current_log_level) if current_log_level in log_levels else 0
                        )
                        log_file = st.text_input("日志文件路径", value=env_config.get("LOG_FILE", "log/app.log"))
                    with col_log2:
                        log_max_bytes = st.number_input(
                            "单个日志文件最大字节数",
                            min_value=1024, max_value=104857600,
                            value=_env_int(env_config, "LOG_MAX_BYTES", 10485760)
                        )
                        log_backup_count = st.number_input(
                            "日志备份文件数量",
                            min_value=1, max_value=10,
                            value=_env_int(env_config, "LOG_BACKUP_COUNT", 3)
                        )

                with st.container(border=True):
                    st.markdown("**🧵 队列与 Redis**")
                    st.caption("Redis 仅在队列驱动为 rq 时使用；async / memory 模式下无需 Redis 服务。")
                    col_queue1, col_queue2, col_queue3 = st.columns(3)
                    with col_queue1:
                        queue_options = ["async", "memory", "rq"]
                        current_queue = env_config.get("QUEUE_DRIVER", "async")
                        queue_driver = st.selectbox(
                            "队列驱动", queue_options,
                            index=queue_options.index(current_queue) if current_queue in queue_options else 0
                        )
                    with col_queue2:
                        redis_host = st.text_input("Redis 主机", value=env_config.get("REDIS_HOST", "127.0.0.1"))
                    with col_queue3:
                        redis_port = st.number_input(
                            "Redis 端口",
                            min_value=1, max_value=65535,
                            value=_env_int(env_config, "REDIS_PORT", 6379)
                        )

                with st.container(border=True):
                    st.markdown("**⏰ 定时任务**")
                    report_cron = st.text_input(
                        "工作日报发送时间 (Cron)",
                        value=env_config.get("REPORT_CRONTAB_EXPRESSION", "0 18 * * 1-5"),
                        help="标准 5 段 cron 表达式，例如 0 18 * * 1-5 表示工作日 18:00 发送"
                    )
            
            # ---------------------------- 通知推送 ----------------------------
            with t_notify:
                with st.container(border=True):
                    st.markdown("**📮 推送模式**")
                    col_mode1, col_mode2 = st.columns([1, 2])
                    with col_mode1:
                        notification_modes = ["detailed", "simplified"]
                        current_mode = env_config.get("NOTIFICATION_MODE", "detailed")
                        notification_mode = st.selectbox(
                            "消息推送模式",
                            options=notification_modes,
                            index=notification_modes.index(current_mode) if current_mode in notification_modes else 0
                        )
                    with col_mode2:
                        st.caption("📄 **detailed 详细模式**：包含完整的AI审查结果、提交列表等详细信息")
                        st.caption("📋 **simplified 简化模式**：仅显示关键信息和简要评论，消息更简洁")

                st.markdown("**📢 通知渠道**")
                col9, col10, col11 = st.columns(3)

                with col9:
                    with st.container(border=True):
                        st.markdown("**钉钉**")
                        dingtalk_enabled = st.checkbox("启用钉钉通知", value=env_config.get("DINGTALK_ENABLED", "0") == "1")
                        dingtalk_webhook = st.text_input("钉钉 Webhook URL", value=env_config.get("DINGTALK_WEBHOOK_URL", ""), type="password")

                with col10:
                    with st.container(border=True):
                        st.markdown("**企业微信**")
                        wecom_enabled = st.checkbox("启用企业微信通知", value=env_config.get("WECOM_ENABLED", "0") == "1")
                        wecom_webhook = st.text_input("企业微信 Webhook URL", value=env_config.get("WECOM_WEBHOOK_URL", ""), type="password")

                with col11:
                    with st.container(border=True):
                        st.markdown("**飞书**")
                        feishu_enabled = st.checkbox("启用飞书通知", value=env_config.get("FEISHU_ENABLED", "0") == "1")
                        feishu_webhook = st.text_input("飞书 Webhook URL", value=env_config.get("FEISHU_WEBHOOK_URL", ""), type="password")

                with st.container(border=True):
                    st.markdown("**🪝 自定义 Webhook**")
                    st.caption("审查完成后额外向该地址推送一份结果，便于对接自建系统。")
                    col_webhook1, col_webhook2 = st.columns([1, 2])
                    with col_webhook1:
                        extra_webhook_enabled = st.checkbox("启用自定义 Webhook", value=env_config.get("EXTRA_WEBHOOK_ENABLED", "0") == "1")
                    with col_webhook2:
                        extra_webhook_url = st.text_input("自定义 Webhook URL", value=env_config.get("EXTRA_WEBHOOK_URL", ""), type="password")
            
            # ---------------------------- 代码平台 ----------------------------
            with t_repo:
                st.caption("平台的启用/停用开关在「🚀 基础」标签页设置，这里配置各平台的访问凭证与审查参数。")

                col_repo1, col_repo2 = st.columns(2)
                with col_repo1:
                    with st.container(border=True):
                        st.markdown("**🔗 GitLab**")
                        gitlab_url = st.text_input("GitLab URL", value=env_config.get("GITLAB_URL", ""), placeholder="https://gitlab.example.com")
                        gitlab_token = st.text_input("GitLab Access Token", value=env_config.get("GITLAB_ACCESS_TOKEN", ""), type="password", placeholder="glpat-xxxxxxxxxxxxxxxxxxxx")
                        push_review_enabled = st.checkbox("启用 Push 审查", value=env_config.get("PUSH_REVIEW_ENABLED", "1") == "1")
                        merge_protected_only = st.checkbox("仅审查受保护分支的 MR", value=env_config.get("MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED", "1") == "1")

                with col_repo2:
                    with st.container(border=True):
                        st.markdown("**🐙 GitHub**")
                        github_url = st.text_input("GitHub URL", value=env_config.get("GITHUB_URL", "https://github.com"),
                                                   help="GitHub Enterprise 用户请填写自建地址")
                        github_token = st.text_input("GitHub Access Token", value=env_config.get("GITHUB_ACCESS_TOKEN", ""), type="password", placeholder="ghp_xxxxxxxxxxxxxxxxxxxx")

                with st.container(border=True):
                    st.markdown("**📂 SVN**")
                    col_svn1, col_svn2, col_svn3 = st.columns(3)
                    with col_svn1:
                        svn_review_enabled = st.checkbox(
                            "启用 SVN 代码审查",
                            value=env_config.get("SVN_REVIEW_ENABLED", "1") == "1",
                            help="关闭后仅记录提交信息，不调用AI审查"
                        )
                    with col_svn2:
                        svn_check_crontab = st.text_input(
                            "默认检查周期 (Cron)",
                            value=env_config.get("SVN_CHECK_CRONTAB", "*/30 * * * *"),
                            help="仓库未单独配置 check_crontab 时使用该默认值"
                        )
                    with col_svn3:
                        svn_check_limit = st.number_input(
                            "单次检查最大提交数",
                            min_value=1, max_value=1000,
                            value=_env_int(env_config, "SVN_CHECK_LIMIT", 100)
                        )

                    st.markdown("**🔍 增强 Merge 检测**")
                    col_merge1, col_merge2 = st.columns([1, 2])
                    with col_merge1:
                        use_enhanced_merge = st.checkbox(
                            "启用增强 Merge 检测",
                            value=env_config.get("USE_ENHANCED_MERGE_DETECTION", "0") == "1",
                            help="多维度检测算法，比仅匹配提交信息关键字更准确"
                        )
                    with col_merge2:
                        merge_threshold = st.slider(
                            "检测置信度阈值",
                            min_value=0.1, max_value=1.0,
                            value=_env_float(env_config, "MERGE_DETECTION_THRESHOLD", 0.45),
                            step=0.05,
                            help="≤0.4 宽松 / 0.4~0.6 平衡 / >0.6 严格，推荐 0.4~0.5"
                        )

                    # 解析已保存的SVN仓库配置
                    current_svn_config = env_config.get("SVN_REPOSITORIES", "[]")
                    try:
                        parsed_repos = json.loads(current_svn_config) if current_svn_config and current_svn_config.strip() else []
                        formatted_config = json.dumps(parsed_repos, indent=2, ensure_ascii=False)
                        svn_repos = [repo for repo in parsed_repos if isinstance(repo, dict)] if isinstance(parsed_repos, list) else []
                    except json.JSONDecodeError:
                        svn_repos = []
                        formatted_config = current_svn_config or "[]"

                    st.markdown("**📋 仓库列表**")
                    col_svn_stats1, col_svn_stats2, col_svn_stats3 = st.columns(3)
                    with col_svn_stats1:
                        st.metric("已配置仓库", len(svn_repos))
                    with col_svn_stats2:
                        if svn_repos:
                            enabled_count = sum(1 for repo in svn_repos if repo.get('enable_merge_review', True))
                            st.metric("启用Merge审查", f"{enabled_count}/{len(svn_repos)}")
                        else:
                            st.metric("启用Merge审查", "0/0")
                    with col_svn_stats3:
                        if svn_repos:
                            avg_hours = sum(repo.get('check_hours', 24) for repo in svn_repos) / len(svn_repos)
                            st.metric("平均检查间隔", f"{avg_hours:.1f}h")
                        else:
                            st.metric("平均检查间隔", "N/A")

                    if svn_repos:
                        for index, repo in enumerate(svn_repos[:5], start=1):
                            merge_status = "✅" if repo.get('enable_merge_review', True) else "❌"
                            st.caption(f"{index}. {repo.get('name', 'Unnamed')} {merge_status} — {repo.get('remote_url', 'No URL')}")
                        if len(svn_repos) > 5:
                            st.caption(f"... 还有 {len(svn_repos) - 5} 个仓库")
                    else:
                        st.caption("暂未配置任何SVN仓库，保存空数组表示不监控任何仓库。")

                    svn_config_text = st.text_area(
                        "仓库配置 (JSON 数组)",
                        value=formatted_config,
                        height=220,
                        help="保存时会校验 JSON 格式；每个元素支持 name / remote_url / local_path / username / password / check_crontab / check_limit / enable_merge_review 等字段"
                    )

            # --------------------------- Prompt模板 ---------------------------
            with t_prompt:
                st.caption("通过 YAML 编辑器自定义 AI 代码审查的 Prompt 模板，保存后写入 conf/prompt_templates.yml。")

                # 读取当前prompt模板
                import yaml
                prompt_templates_file = "conf/prompt_templates.yml"
                current_prompt_config = {}
                formatted_prompt_config = ""  # 兜底默认值

                try:
                    if os.path.exists(prompt_templates_file):
                        with open(prompt_templates_file, 'r', encoding='utf-8') as f:
                            current_prompt_config = yaml.safe_load(f) or {}
                            # 直接读取原始YAML内容
                        with open(prompt_templates_file, 'r', encoding='utf-8') as f:
                            formatted_prompt_config = f.read()
                except Exception as e:
                    st.warning(f"⚠️ 读取Prompt模板文件失败: {e}")
                    current_prompt_config = {}
                    formatted_prompt_config = """code_review_prompt:
  system_prompt: |-
    你是一位资深的软件开发工程师，专注于代码的规范性、功能性、安全性和稳定性。
    审查风格：{{ style }}
  user_prompt: |-
    以下是代码变更，请以{{ style }}风格审查：
    
    结构化diff JSON内容：
    {diffs_text}
    
    提交历史：
    {commits_text}"""
                
                # 当前模板状态概览
                prompt_labels = {
                    'code_review_prompt': '📌 主审查',
                    'code_review_batch_prompt': '📦 分批审查',
                    'code_review_merge_prompt': '🔗 合并报告',
                }
                prompt_status_rows = []
                for pkey, plabel in prompt_labels.items():
                    cfg = current_prompt_config.get(pkey) or {}
                    sys_len = len(cfg.get('system_prompt', '') or '')
                    usr_len = len(cfg.get('user_prompt', '') or '')
                    prompt_status_rows.append({
                        "模板": plabel,
                        "系统Prompt": f"{sys_len} 字符" if sys_len else "未设置",
                        "用户Prompt": f"{usr_len} 字符" if usr_len else "未设置",
                        "状态": "✅ 完整" if (sys_len and usr_len) else "⚠️ 不完整",
                    })
                st.dataframe(pd.DataFrame(prompt_status_rows), use_container_width=True, hide_index=True)

                # YAML配置编辑器
                prompt_config_text = st.text_area(
                    "Prompt模板配置 (YAML)",
                    value=formatted_prompt_config,
                    height=420,
                    help="保存时会校验 YAML 格式，并要求三个模板都包含 system_prompt 与 user_prompt"
                )
                st.caption("⚠️ 三个模板需保持同一套评分标准与「总分: XX分」输出格式，否则评分会解析失败。")

            # 保存系统配置按钮
            if st.form_submit_button("💾 保存系统配置", use_container_width=True, type="primary"):
                # 处理SVN配置（从文本编辑器读取）
                svn_config_final = "[]"  # 默认空配置
                if svn_config_text and svn_config_text.strip():
                    try:
                        # 验证JSON格式
                        parsed_svn = json.loads(svn_config_text)
                        if isinstance(parsed_svn, list):
                            # 将JSON压缩为单行格式，避免换行导致的.env文件解析问题
                            svn_config_final = json.dumps(parsed_svn, ensure_ascii=False, separators=(',', ':'))
                        else:
                            st.error("❌ SVN配置必须是一个数组格式")
                            st.stop()
                    except json.JSONDecodeError as e:
                        st.error(f"❌ SVN配置JSON格式错误: {e}")
                        st.stop()
                
                new_config = {
                    # AI模型
                    "LLM_PROVIDER": llm_provider,
                    "DEEPSEEK_API_KEY": deepseek_key,
                    "DEEPSEEK_API_BASE_URL": deepseek_base,
                    "DEEPSEEK_API_MODEL": deepseek_model,
                    "OPENAI_API_KEY": openai_key,
                    "OPENAI_API_BASE_URL": openai_base,
                    "OPENAI_API_MODEL": openai_model,
                    "ZHIPUAI_API_KEY": zhipuai_key,
                    "ZHIPUAI_API_MODEL": zhipuai_model,
                    "QWEN_API_KEY": qwen_key,
                    "QWEN_API_BASE_URL": qwen_base,
                    "QWEN_API_MODEL": qwen_model,
                    "JEDI_API_KEY": jedi_key,
                    "JEDI_API_BASE_URL": jedi_base,
                    "JEDI_API_MODEL": jedi_model,
                    "OLLAMA_API_BASE_URL": ollama_base,
                    "OLLAMA_API_MODEL": ollama_model,

                    # 审查设置
                    "REVIEW_MAX_TOKENS": str(review_max_tokens),
                    "SUPPORTED_EXTENSIONS": supported_extensions,
                    "EXCLUDE_PATTERNS": exclude_patterns,
                    "SVN_DIFF_CONTEXT_LINES": str(svn_diff_context_lines),
                    "AGENTIC_REVIEW_ENABLED": "1" if agentic_review_enabled else "0",
                    "AGENTIC_REVIEW_MAX_TOOL_ROUNDS": str(agentic_max_tool_rounds),
                    "VERSION_TRACKING_ENABLED": "1" if version_tracking_enabled else "0",
                    "REUSE_PREVIOUS_REVIEW_RESULT": "1" if reuse_previous_review else "0",
                    "VERSION_TRACKING_RETENTION_DAYS": str(retention_days),

                    # 平台开关
                    "SVN_CHECK_ENABLED": "1" if svn_enabled else "0",
                    "GITLAB_ENABLED": "1" if gitlab_enabled else "0",
                    "GITHUB_ENABLED": "1" if github_enabled else "0",

                    # GitLab
                    "GITLAB_URL": gitlab_url,
                    "GITLAB_ACCESS_TOKEN": gitlab_token,
                    "PUSH_REVIEW_ENABLED": "1" if push_review_enabled else "0",
                    "MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED": "1" if merge_protected_only else "0",

                    # GitHub
                    "GITHUB_URL": github_url,
                    "GITHUB_ACCESS_TOKEN": github_token,

                    # SVN
                    "SVN_REVIEW_ENABLED": "1" if svn_review_enabled else "0",
                    "SVN_CHECK_CRONTAB": svn_check_crontab,
                    "SVN_CHECK_LIMIT": str(svn_check_limit),
                    "SVN_REPOSITORIES": svn_config_final,
                    "USE_ENHANCED_MERGE_DETECTION": "1" if use_enhanced_merge else "0",
                    "MERGE_DETECTION_THRESHOLD": str(round(merge_threshold, 2)),

                    # 通知推送
                    "NOTIFICATION_MODE": notification_mode,
                    "DINGTALK_ENABLED": "1" if dingtalk_enabled else "0",
                    "DINGTALK_WEBHOOK_URL": dingtalk_webhook,
                    "WECOM_ENABLED": "1" if wecom_enabled else "0",
                    "WECOM_WEBHOOK_URL": wecom_webhook,
                    "FEISHU_ENABLED": "1" if feishu_enabled else "0",
                    "FEISHU_WEBHOOK_URL": feishu_webhook,
                    "EXTRA_WEBHOOK_ENABLED": "1" if extra_webhook_enabled else "0",
                    "EXTRA_WEBHOOK_URL": extra_webhook_url,

                    # 系统运行
                    "API_PORT": api_port,
                    "API_URL": api_url,
                    "UI_PORT": ui_port,
                    "UI_URL": ui_url,
                    "TZ": timezone,
                    "LOG_LEVEL": log_level,
                    "LOG_FILE": log_file,
                    "LOG_MAX_BYTES": str(log_max_bytes),
                    "LOG_BACKUP_COUNT": str(log_backup_count),
                    "QUEUE_DRIVER": queue_driver,
                    "REDIS_HOST": redis_host,
                    "REDIS_PORT": str(redis_port),
                    "REPORT_CRONTAB_EXPRESSION": report_cron,

                    # Dashboard
                    "DASHBOARD_USER": dashboard_user,
                    "DASHBOARD_PASSWORD": dashboard_password,
                }
                
                # 保存Prompt模板配置
                prompt_save_success = True
                try:
                    # 处理Prompt配置（从YAML文本编辑器读取）
                    if prompt_config_text and prompt_config_text.strip():
                        try:
                            # 验证YAML格式
                            parsed_prompt = yaml.safe_load(prompt_config_text)
                            required_keys = ['code_review_prompt', 'code_review_batch_prompt', 'code_review_merge_prompt']
                            if isinstance(parsed_prompt, dict) and all(k in parsed_prompt for k in required_keys):
                                # 校验每个 prompt 必须有 system_prompt 和 user_prompt
                                missing_fields = []
                                for pkey in required_keys:
                                    pval = parsed_prompt.get(pkey, {})
                                    if not isinstance(pval, dict):
                                        missing_fields.append(f"{pkey}(不是字典)")
                                    else:
                                        if 'system_prompt' not in pval:
                                            missing_fields.append(f"{pkey}.system_prompt")
                                        if 'user_prompt' not in pval:
                                            missing_fields.append(f"{pkey}.user_prompt")
                                if missing_fields:
                                    st.error(f"❌ Prompt配置结构不完整，缺少: {', '.join(missing_fields)}")
                                    prompt_save_success = False
                                    st.stop()

                                # 直接保存YAML文本到文件
                                prompt_templates_file = "conf/prompt_templates.yml"
                                
                                # 确保目录存在
                                os.makedirs(os.path.dirname(prompt_templates_file), exist_ok=True)
                                
                                with open(prompt_templates_file, 'w', encoding='utf-8') as f:
                                    f.write(prompt_config_text)
                            else:
                                missing = [k for k in required_keys if k not in (parsed_prompt if isinstance(parsed_prompt, dict) else {})]
                                st.error(f"❌ Prompt配置缺少字段: {', '.join(missing) if missing else '配置格式错误'}")
                                prompt_save_success = False
                        except yaml.YAMLError as e:
                            st.error(f"❌ Prompt配置YAML格式错误: {e}")
                            prompt_save_success = False
                    else:
                        # 配置为空，读取当前磁盘上的配置文件作为默认值回显
                        try:
                            default_config_path = "conf/prompt_templates.yml"
                            if os.path.exists(default_config_path):
                                with open(default_config_path, 'r', encoding='utf-8') as f:
                                    default_prompt_config = f.read()
                            else:
                                # 磁盘也没有，使用 conf_templates 下的模板
                                template_path = "conf_templates/prompt_templates.yml"
                                if os.path.exists(template_path):
                                    with open(template_path, 'r', encoding='utf-8') as f:
                                        default_prompt_config = f.read()
                                else:
                                    default_prompt_config = ""
                        except Exception:
                            default_prompt_config = ""
                        
                        if default_prompt_config.strip():
                            prompt_templates_file = "conf/prompt_templates.yml"
                            os.makedirs(os.path.dirname(prompt_templates_file), exist_ok=True)
                            with open(prompt_templates_file, 'w', encoding='utf-8') as f:
                                f.write(default_prompt_config)
                        else:
                            st.warning("⚠️ 未找到默认Prompt模板，已跳过")
                    
                except Exception as e:
                    st.error(f"❌ Prompt模板保存失败: {e}")
                    prompt_save_success = False
                
                # 保存环境配置
                try:
                    env_save_success = _save_env_config(config_manager, new_config)

                    if env_save_success and prompt_save_success:
                        st.success("✅ 系统配置与Prompt模板已保存")
                        try:
                            if apply_config_changes():
                                st.success("✅ 配置已重载生效")
                            else:
                                st.warning("⚠️ 配置已保存，但重载未完全成功，可点击下方「🔄 立即重载配置」重试")
                        except Exception as e:
                            st.warning(f"⚠️ 配置已保存，但自动重载失败: {e}")
                    else:
                        if not env_save_success:
                            st.error("❌ 环境配置保存失败，请检查 conf/.env 的写入权限")
                        if not prompt_save_success:
                            st.error("❌ Prompt模板保存失败")
                except Exception as e:
                    st.error(f"❌ 保存配置时出现错误: {str(e)}")

        # 配置操作按钮 - 移出form范围
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
        st.caption("查看所有配置项及其当前状态，敏感信息（密钥 / Token / Webhook）已自动打码。")

        try:
            current_config = config_manager.get_env_config() or {}
        except Exception as e:
            st.error(f"❌ 读取配置失败: {e}")
            current_config = {}

        if not current_config:
            st.warning("⚠️ 无法读取环境变量配置")
        else:
            key_to_category = {
                key: category
                for category, keys in CONFIG_CATEGORIES.items()
                for key in keys
            }

            overview_rows = []
            for key, value in current_config.items():
                raw_value = str(value) if value else ""
                overview_rows.append({
                    "分类": key_to_category.get(key, "🧩 其他"),
                    "配置项": key,
                    "当前值": _mask_value(raw_value) if _is_sensitive_key(key) else (raw_value or "未设置"),
                    "状态": "✅ 已配置" if raw_value.strip() else "⚠️ 未配置",
                })
            overview_df = pd.DataFrame(overview_rows).sort_values(["分类", "配置项"])

            total_items = len(overview_df)
            configured_items = int((overview_df["状态"] == "✅ 已配置").sum())
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("总配置项", total_items)
            col_stat2.metric("已配置项", configured_items)
            col_stat3.metric("配置完成度", f"{(configured_items / total_items * 100) if total_items else 0:.1f}%")

            col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])
            with col_filter1:
                category_options = ["全部"] + sorted(overview_df["分类"].unique().tolist())
                selected_category = st.selectbox("按分类筛选", category_options, key="overview_category")
            with col_filter2:
                keyword = st.text_input("搜索配置项", placeholder="输入配置项名称关键字", key="overview_keyword")
            with col_filter3:
                only_unconfigured = st.checkbox("仅看未配置", key="overview_only_unconfigured")

            filtered_df = overview_df
            if selected_category != "全部":
                filtered_df = filtered_df[filtered_df["分类"] == selected_category]
            if keyword.strip():
                filtered_df = filtered_df[filtered_df["配置项"].str.contains(keyword.strip(), case=False, na=False, regex=False)]
            if only_unconfigured:
                filtered_df = filtered_df[filtered_df["状态"] == "⚠️ 未配置"]

            if filtered_df.empty:
                st.info("没有符合筛选条件的配置项")
            else:
                st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=460)

            with st.expander("📝 Prompt 模板文件状态", expanded=False):
                import yaml
                prompt_templates_file = "conf/prompt_templates.yml"
                try:
                    if os.path.exists(prompt_templates_file):
                        with open(prompt_templates_file, 'r', encoding='utf-8') as f:
                            prompt_config = yaml.safe_load(f) or {}
                        prompt_rows = []
                        for pkey, plabel in (
                            ('code_review_prompt', '📌 主审查'),
                            ('code_review_batch_prompt', '📦 分批审查'),
                            ('code_review_merge_prompt', '🔗 合并报告'),
                        ):
                            cfg = prompt_config.get(pkey) or {}
                            sys_len = len(cfg.get('system_prompt', '') or '')
                            usr_len = len(cfg.get('user_prompt', '') or '')
                            prompt_rows.append({
                                "模板": plabel,
                                "系统Prompt": f"{sys_len} 字符" if sys_len else "未设置",
                                "用户Prompt": f"{usr_len} 字符" if usr_len else "未设置",
                                "状态": "✅ 完整" if (sys_len and usr_len) else "⚠️ 不完整",
                            })
                        st.dataframe(pd.DataFrame(prompt_rows), use_container_width=True, hide_index=True)
                    else:
                        st.warning(f"⚠️ 模板文件不存在: {prompt_templates_file}")
                except Exception as e:
                    st.error(f"❌ 读取Prompt模板失败: {e}")
    
    with tab3:
        st.caption("快速套用常见环境的配置组合，或对当前配置做导出、重置等维护操作。")

        col_template1, col_template2 = st.columns(2)

        with col_template1:
            with st.container(border=True):
                st.markdown("**🔧 环境模板**")
                st.caption("模板只覆盖下表列出的配置项，其余配置保持不变。")

                selected_template = st.selectbox("选择模板", list(ENV_TEMPLATES.keys()), key="env_template_select")
                template_config = ENV_TEMPLATES[selected_template]

                st.dataframe(
                    pd.DataFrame([
                        {"配置项": key, "模板值": value, "当前值": env_config.get(key, "未设置")}
                        for key, value in template_config.items()
                    ]),
                    use_container_width=True, hide_index=True
                )

                if st.button(f"应用「{selected_template}」模板", key="apply_template", use_container_width=True):
                    try:
                        if _save_env_config(config_manager, template_config):
                            st.success(f"✅ 已应用「{selected_template}」模板")
                            if apply_config_changes():
                                st.success("✅ 配置已重载生效")
                            else:
                                st.warning("⚠️ 配置已保存，但重载未完全成功，建议检查服务状态")
                        else:
                            st.error("❌ 应用模板失败")
                    except Exception as e:
                        st.error(f"❌ 应用模板失败: {e}")

        with col_template2:
            with st.container(border=True):
                st.markdown("**📥 导出配置**")
                st.caption("⚠️ 导出内容包含 API Key、Webhook 等明文敏感信息，勾选后才会生成下载数据。")
                export_confirmed = st.checkbox("我确认要导出含明文密钥的配置", key="export_config_confirm")
                if export_confirmed:
                    try:
                        export_lines = ["# AI代码审查系统配置文件",
                                        f"# 导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
                        for key, value in (config_manager.get_env_config() or {}).items():
                            export_lines.append(f"{key}={ConfigManager._escape_env_value(value)}")
                        st.download_button(
                            label="下载 .env 配置文件",
                            data="\n".join(export_lines) + "\n",
                            file_name=f"env_config_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.env",
                            mime="text/plain",
                            use_container_width=True,
                            key="export_config"
                        )
                    except Exception as e:
                        st.error(f"❌ 导出配置失败: {e}")

            with st.container(border=True):
                st.markdown("**🔄 重置配置**")
                st.caption("⚠️ 会把 conf/.env 恢复为默认模板，已填写的密钥、仓库配置都将丢失。")
                reset_confirmed = st.checkbox("我确认要重置全部配置", key="reset_config_confirm")
                if st.button("重置为默认配置", key="reset_config",
                             disabled=not reset_confirmed, use_container_width=True):
                    try:
                        if config_manager.reset_env_config():
                            st.success("✅ 配置已重置为默认值，请重启应用使配置完全生效")
                        else:
                            st.error("❌ 重置配置失败")
                    except Exception as e:
                        st.error(f"❌ 重置配置失败: {e}")

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
