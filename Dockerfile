# 使用官方的 Python 基础镜像
FROM python:3.10-slim AS base

# 设置工作目录
WORKDIR /app

# 安装 supervisord 作为进程管理工具
RUN apt-get update && apt-get install -y --no-install-recommends supervisor subversion && rm -rf /var/lib/apt/lists/*

# 复制项目文件&创建必要的文件夹
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p log data conf scripts
COPY biz ./biz
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY conf/prompt_templates.yml ./conf/prompt_templates.yml
COPY conf/.env.dist ./conf/.env.dist
COPY scripts/init_env.py ./scripts/init_env.py

# 创建启动脚本来初始化环境
RUN echo '#!/bin/bash\n\
# 初始化环境配置\n\
if [ ! -f /app/conf/.env ]; then\n\
    echo "=== Initializing environment configuration ==="\n\
    python /app/scripts/init_env.py\n\
else\n\
    echo "=== Environment configuration found ==="\n\
fi\n\
\n\
# 加载环境变量\n\
if [ -f /app/conf/.env ]; then\n\
    echo "Loading environment variables from .env file..."\n\
    export $(grep -v "^#" /app/conf/.env | xargs)\n\
fi\n\
\n\
echo "=== Starting services ==="\n\
# 启动supervisord\n\
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf\n\
' > /app/start.sh && chmod +x /app/start.sh

# 使用启动脚本
CMD ["/app/start.sh"]

FROM base AS app
COPY conf/supervisord.app.conf /etc/supervisor/conf.d/supervisord.conf
# 暴露 Flask 和 Streamlit 的端口
EXPOSE 5001 5002

FROM base AS worker
COPY ./conf/supervisord.worker.conf /etc/supervisor/conf.d/supervisord.conf