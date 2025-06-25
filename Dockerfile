# 使用官方的 Python 基础镜像
FROM python:3.12-slim AS base

# 设置工作目录
WORKDIR /app

# 安装 supervisord 作为进程管理工具
RUN apt-get update && apt-get install -y --no-install-recommends supervisor subversion && rm -rf /var/lib/apt/lists/*

# 复制项目文件&创建必要的文件夹
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p log data scripts .streamlit conf_templates
COPY biz ./biz
COPY ui_components ./ui_components
COPY conf ./conf_templates
COPY .streamlit ./.streamlit
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY scripts/ ./scripts/

# 创建启动脚本来初始化环境
RUN echo '#!/bin/bash\n\
# Docker 配置自动初始化\n\
echo "=== Docker Configuration Initialization ==="\n\
python /app/scripts/docker_init.py\n\
init_result=$?\n\
\n\
if [ $init_result -ne 0 ]; then\n\
    echo "❌ Docker 配置初始化失败，退出..."\n\
    exit $init_result\n\
fi\n\
\n\
echo "=== Starting services ==="\n\
# 启动supervisord\n\
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf\n\
' > /app/start.sh && chmod +x /app/start.sh

# 使用启动脚本
CMD ["/app/start.sh"]

FROM base AS app
# 设置运行模式环境变量
ENV DOCKER_RUN_MODE=app
# supervisord 配置将在启动时自动复制
# 暴露 Flask 和 Streamlit 的端口
EXPOSE 5001 5002

FROM base AS worker
# 设置运行模式环境变量
ENV DOCKER_RUN_MODE=worker
# supervisord 配置将在启动时自动复制