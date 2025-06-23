# AI代码审查系统部署完整指南

## 📋 目录
- [系统概述](#系统概述)
- [环境要求](#环境要求)
- [部署方案](#部署方案)
- [配置说明](#配置说明)
- [UI功能详解](#ui功能详解)
- [常见问题](#常见问题)
- [性能优化](#性能优化)
- [维护指南](#维护指南)

## 🔍 系统概述

AI代码审查系统是一个现代化的代码质量管理平台，集成了多种大模型（DeepSeek、ZhipuAI、OpenAI等），支持GitLab/GitHub webhook触发和SVN定时检测，提供实时的代码审查和可视化仪表板。

### 核心特性
- 🤖 **多模型支持**: 支持主流AI大模型
- 🔄 **多版本控制**: GitLab、GitHub、SVN全支持
- 📊 **现代化UI**: 响应式设计，数据可视化
- 🔐 **安全认证**: 内置用户管理系统
- 📱 **移动友好**: 支持移动端访问
- ⚡ **高性能**: 缓存优化，快速响应

## 💻 环境要求

### 基础要求
- **Python**: 3.8+ (推荐 3.10+)
- **操作系统**: Windows/Linux/macOS
- **内存**: 最低2GB，推荐4GB+
- **磁盘**: 最低1GB可用空间

### 依赖组件
- **Streamlit**: Web UI框架
- **SQLite**: 数据存储
- **Matplotlib**: 图表生成
- **Pandas**: 数据处理
- **其他**: 详见 requirements.txt

## 🚀 部署方案

### 方案一：快速部署（推荐）

1. **克隆项目**
```bash
git clone https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB.git
cd AI-CODEREVIEW-GITLAB
```

2. **环境配置**
```bash
# 复制配置文件
cp conf/.env.dist conf/.env

# 编辑配置文件（按需修改）
nano conf/.env
```

3. **一键启动**
```bash
# Windows
run_ui.bat

# Linux/Mac
chmod +x run_ui.sh
./run_ui.sh
```

### 方案二：Docker部署

1. **使用Docker Compose**
```bash
docker-compose up -d
```

2. **验证部署**
- API服务: http://localhost:5001
- 仪表板: http://localhost:5002

### 方案三：手动部署

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **启动服务**
```bash
# 启动API服务
python api.py

# 启动仪表板（新终端）
streamlit run ui.py --server.port=5002 --server.address=0.0.0.0
```

## ⚙️ 配置说明

### 基础配置 (.env)
```bash
# AI模型配置
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key

# GitLab配置
GITLAB_ACCESS_TOKEN=your_token

# 仪表板配置
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=your_secure_password

# 消息推送配置
DINGTALK_ENABLED=1
DINGTALK_WEBHOOK_URL=your_webhook_url
```

### 高级配置 (dashboard_config.py)
```python
# UI个性化配置
DASHBOARD_TITLE = "我的代码审查仪表板"
DASHBOARD_ICON = "🔍"
CHART_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1"]

# 性能配置
ENABLE_CACHING = True
CACHE_TTL_MINUTES = 15
AUTO_REFRESH_INTERVAL = 300
```

## 📊 UI功能详解

### 登录系统
- 🔐 安全认证机制
- 👤 用户会话管理
- 🕐 自动超时保护

### 数据概览
- 📈 关键指标卡片
- 📊 实时统计数据
- 🎯 质量趋势分析

### 图表分析
- 📊 TOP10排行榜
- 📈 时间趋势图
- 🥧 分布饼图
- 📉 评分分析图

### 数据管理
- 🔍 多维度筛选
- 📋 详细数据表格
- 📥 数据导出功能
- 🔄 实时数据刷新

### 高级功能
- ⚙️ 个性化设置
- 📚 内置帮助文档
- 📱 响应式布局
- 🖥️ 系统监控

## 🔧 常见问题

### Q1: 启动失败怎么办？
**A:** 检查以下项目：
1. Python版本是否符合要求
2. 依赖是否完整安装
3. 端口是否被占用
4. 配置文件是否正确

```bash
# 检查Python版本
python --version

# 重新安装依赖
pip install -r requirements.txt --upgrade

# 检查端口占用
netstat -an | findstr :8501
```

### Q2: 图表显示乱码
**A:** 中文字体问题：
1. 系统已自动配置中文字体
2. 如仍有问题，请安装系统中文字体
3. Windows: 确保有SimHei字体
4. Linux: 安装中文字体包

### Q3: 数据不显示
**A:** 检查数据源：
1. 确认数据库文件存在
2. 检查webhook配置
3. 验证API服务运行状态
4. 查看日志文件

### Q4: 性能慢
**A:** 优化建议：
1. 启用缓存功能
2. 减少数据查询范围
3. 增加系统内存
4. 使用SSD存储

## ⚡ 性能优化

### 缓存优化
```python
# 启用缓存
ENABLE_CACHING = True
CACHE_TTL_MINUTES = 15
```

### 数据库优化
```sql
-- 创建索引
CREATE INDEX idx_updated_at ON merge_request_reviews(updated_at);
CREATE INDEX idx_project_name ON merge_request_reviews(project_name);
```

### 系统优化
- 定期清理日志文件
- 优化数据库大小
- 监控系统资源使用

## 🔧 维护指南

### 日常维护
1. **日志管理**
   - 定期检查 log/app.log
   - 清理过期日志文件

2. **数据备份**
   - 备份 data/data.db
   - 导出重要配置

3. **更新升级**
   - 定期更新依赖
   - 关注版本发布

### 故障排除
1. **服务重启**
   ```bash
   # 重启API服务
   pkill -f api.py
   python api.py &
   
   # 重启UI服务
   pkill -f streamlit
   ./run_ui.sh
   ```

2. **清理缓存**
   ```bash
   # 清理Python缓存
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   
   # 重置Streamlit缓存
   streamlit cache clear
   ```

3. **健康检查**
   ```bash
   # 检查API服务
   curl http://localhost:5001
   
   # 检查UI服务
   curl http://localhost:8501
   ```

### 监控指标
- CPU使用率 < 80%
- 内存使用率 < 70%
- 磁盘使用率 < 90%
- API响应时间 < 2秒

## 📞 技术支持

如遇到问题，请按以下顺序寻求帮助：

1. **查看文档**: [UI使用指南](ui_guide.md)
2. **检查日志**: log/app.log
3. **GitHub Issues**: 提交问题报告
4. **微信群**: 加入技术交流群

---

**版本**: v2.0  
**更新日期**: 2025年6月  
**维护者**: AI代码审查团队

> 💡 **提示**: 本系统持续优化中，建议定期更新到最新版本以获得最佳体验。
