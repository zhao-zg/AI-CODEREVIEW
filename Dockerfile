# 使用官方的 Python 基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖和构建工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    subversion \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip 和安装构建工具
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制 requirements 文件
COPY requirements.txt .
# 安装 Python 依赖
# 使用 --no-cache-dir 选项来避免缓存，减少镜像大小
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING=utf-8
ENV DOCKER_ENV=true

RUN mkdir -p log data scripts .streamlit conf_templates
COPY biz ./biz
COPY ui_components ./ui_components
COPY conf_templates ./conf_templates
COPY .streamlit ./.streamlit
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY scripts/ ./scripts/

# 创建启动脚本来初始化环境
RUN echo '#!/bin/bash\n\
# Docker 配置自动初始化\n\
echo "=== Docker Configuration Initialization ==="\n\
\n\
# 显示环境变量状态（ENV已设置，无需重复export）\n\
echo "🔧 Python环境: PYTHONUNBUFFERED=${PYTHONUNBUFFERED}"\n\
echo "🔧 字符编码: PYTHONIOENCODING=${PYTHONIOENCODING}"\n\
echo "🔧 Docker环境: DOCKER_ENV=${DOCKER_ENV}"\n\
\n\
# 运行配置初始化\n\
echo "🔧 初始化配置..."\n\
python -u /app/scripts/docker_init.py\n\
init_result=$?\n\
\n\
if [ $init_result -ne 0 ]; then\n\
    echo "❌ Docker 配置初始化失败，退出..."\n\
    exit $init_result\n\
fi\n\
\n\
echo "=== Starting AI-CodeReview Service ==="\n\
echo "🚀 启动服务: API (5001) + UI (5002)"\n\
echo "📋 日志级别: ${LOG_LEVEL:-INFO}"\n\
echo "📁 日志文件: ${LOG_FILE:-log/app.log}"\n\
\n\
# 启动supervisord（同时运行API、UI和Worker）\n\
# 使用 -n 参数以非守护进程模式运行，确保日志输出到控制台\n\
echo "🔄 启动 Supervisor..."\n\
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf\n\
' > /app/start.sh && chmod +x /app/start.sh

# 暴露 Flask 和 Streamlit 的端口
EXPOSE 5001 5002

# 使用启动脚本
CMD ["/app/start.sh"]