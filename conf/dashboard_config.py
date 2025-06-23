# AI代码审查仪表板配置文件

# 仪表板基本设置
DASHBOARD_TITLE = "AI 代码审查仪表板"
DASHBOARD_ICON = "🤖"
DASHBOARD_LAYOUT = "wide"  # 可选: wide, centered
DASHBOARD_THEME = "light"  # 可选: light, dark, auto

# 登录设置
DASHBOARD_USER = "admin"
DASHBOARD_PASSWORD = "admin"
SESSION_TIMEOUT_HOURS = 24  # 会话超时时间（小时）

# 数据显示设置
MAX_RECORDS_PER_PAGE = 100  # 每页最大记录数
DEFAULT_CHART_HEIGHT = 400  # 默认图表高度
SHOW_DEBUG_INFO = False     # 是否显示调试信息

# 图表颜色配置
CHART_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57",
    "#FF9FF3", "#54A0FF", "#5F27CD", "#00D2D3", "#FF9F43",
    "#10AC84", "#EE5A24", "#0ABDE3", "#C44569", "#F8B500"
]

# 数据刷新设置
AUTO_REFRESH_ENABLED = True   # 是否启用自动刷新
AUTO_REFRESH_INTERVAL = 300   # 自动刷新间隔（秒）

# 导出设置
ENABLE_DATA_EXPORT = True     # 是否启用数据导出
EXPORT_FORMATS = ["CSV", "JSON", "EXCEL"]  # 支持的导出格式

# 通知设置
ENABLE_NOTIFICATIONS = True   # 是否启用通知
NOTIFICATION_TYPES = ["info", "success", "warning", "error"]

# 高级功能
ENABLE_REAL_TIME_UPDATES = False  # 是否启用实时更新
ENABLE_ADVANCED_FILTERING = True  # 是否启用高级筛选
ENABLE_CHART_INTERACTIONS = True  # 是否启用图表交互

# 移动端优化
MOBILE_FRIENDLY = True        # 是否启用移动端优化
RESPONSIVE_BREAKPOINTS = {    # 响应式断点
    "mobile": 768,
    "tablet": 1024,
    "desktop": 1440
}

# 缓存设置
ENABLE_CACHING = True         # 是否启用缓存
CACHE_TTL_MINUTES = 15        # 缓存生存时间（分钟）
