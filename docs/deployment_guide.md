# 🚀 AI-CodeReview-GitLab 部署指南

## 📋 部署概述

AI-CodeReview-GitLab 是一个基于大模型的自动化代码审查工具，支持多种部署方式，本指南将详细介绍各种部署选项和配置方法。

## 🐳 Docker 部署（推荐）

### 方式一：使用 Docker Hub 镜像

这是最简单的部署方式，直接使用我们发布的官方镜像。

```bash
# 1. 克隆配置文件
git clone https://github.com/zhao-zg/ai-codereview-gitlab.git
cd ai-codereview-gitlab

# 2. 使用 Docker Hub 镜像启动
docker-compose -f docker-compose.dockerhub.yml up -d

# 3. 查看服务状态
docker-compose -f docker-compose.dockerhub.yml ps
```

### 方式二：使用 GitHub Container Registry 镜像

```bash
# 1. 克隆项目
git clone https://github.com/zhao-zg/ai-codereview-gitlab.git
cd ai-codereview-gitlab

# 2. 使用 GHCR 镜像启动
docker-compose up -d

# 3. 查看服务状态
docker-compose ps
```

### 方式三：本地构建部署

```bash
# 1. 克隆项目
git clone https://github.com/zhao-zg/ai-codereview-gitlab.git
cd ai-codereview-gitlab

# 2. 本地构建并启动
docker-compose up --build -d

# 3. 查看构建日志
docker-compose logs -f app
```

## ⚙️ 环境配置

### 基础配置

1. **复制配置文件模板**
```bash
cp conf_templates/.env.dist conf/.env
```

2. **编辑配置文件**
```bash
# 编辑 conf/.env 文件，配置以下关键参数
nano conf/.env
```

### 关键配置项

```env
# ===================
# LLM 配置
# ===================
LLM_PROVIDER=deepseek                    # 选择 LLM 提供商
DEEPSEEK_API_KEY=your_deepseek_api_key   # DeepSeek API密钥
OPENAI_API_KEY=your_openai_api_key       # OpenAI API密钥
ZHIPUAI_API_KEY=your_zhipuai_api_key     # 智谱AI API密钥

# ===================
# GitLab 配置
# ===================
GITLAB_URL=https://gitlab.example.com    # GitLab 服务器地址
GITLAB_TOKEN=your_gitlab_token           # GitLab Access Token
GITLAB_WEBHOOK_SECRET=your_webhook_secret # Webhook 密钥

# ===================
# GitHub 配置  
# ===================
GITHUB_TOKEN=your_github_token           # GitHub Personal Access Token
GITHUB_WEBHOOK_SECRET=your_webhook_secret # GitHub Webhook 密钥

# ===================
# 消息推送配置
# ===================
DINGTALK_WEBHOOK=your_dingtalk_webhook   # 钉钉机器人Webhook
WECOM_WEBHOOK=your_wecom_webhook         # 企业微信机器人Webhook
FEISHU_WEBHOOK=your_feishu_webhook       # 飞书机器人Webhook

# ===================
# 服务配置
# ===================
API_PORT=5001                         # API服务端口
UI_PORT=5002                            # Web界面端口
LOG_LEVEL=INFO                          # 日志级别
TZ=Asia/Shanghai                        # 时区设置
```

## 🔧 高级部署配置

### 多实例部署

对于高负载场景，可以部署多个实例。

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app1:
    image: zzg1189/ai-codereview-gitlab:latest
    ports:
      - "5001:5001"
      - "5002:5002"
    volumes:
      - ./data:/app/data
      - ./conf:/app/conf
    environment:
      - INSTANCE_ID=app1
    
  app2:
    image: zzg1189/ai-codereview-gitlab:latest
    ports:
      - "5003:5001"
      - "5004:5002"
    volumes:
      - ./data:/app/data
      - ./conf:/app/conf
    environment:
      - INSTANCE_ID=app2

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app1
      - app2
```

### 持久化存储配置

```yaml
volumes:
  # 数据持久化
  - ./data:/app/data:rw
  - ./log:/app/log:rw
  - ./conf:/app/conf:ro
  
  # SVN 仓库挂载
  - /path/to/svn/repos:/app/data/svn:ro
  
  # 自定义配置
  - ./custom_configs:/app/custom_configs:ro
```

## 🌐 反向代理配置

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # API 服务代理
    location /api/ {
        proxy_pass http://localhost:5001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Web 界面代理
    location / {
        proxy_pass http://localhost:5002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持 (Streamlit)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Apache 配置示例

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    # API 服务代理
    ProxyPreserveHost On
    ProxyPass /api/ http://localhost:5001/
    ProxyPassReverse /api/ http://localhost:5001/
    
    # Web 界面代理
    ProxyPass / http://localhost:5002/
    ProxyPassReverse / http://localhost:5002/
    
    # WebSocket 支持
    RewriteEngine on
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://localhost:5002/$1" [P,L]
</VirtualHost>
```

## 🔒 安全配置

### HTTPS 配置

1. **获取 SSL 证书**
```bash
# 使用 Let's Encrypt
certbot --nginx -d your-domain.com
```

2. **更新 Nginx 配置**
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # 其他配置...
}
```

### 防火墙配置

```bash
# Ubuntu/Debian
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5001/tcp  # 如果需要直接访问 API
ufw allow 5002/tcp  # 如果需要直接访问 Web 界面

# CentOS/RHEL
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
```

## 📊 监控和日志

### 日志配置

```yaml
# docker-compose.yml 中添加日志配置
services:
  app:
    image: zzg1189/ai-codereview-gitlab:latest
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

### 健康检查

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 监控指标

```bash
# 查看容器状态
docker-compose ps

# 查看资源使用
docker stats

# 查看日志
docker-compose logs -f app

# 检查健康状况
curl http://localhost:5001/health
```

## 🚀 生产环境最佳实践

### 1. 资源配置建议

| 组件 | 最小配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 cores | 4+ cores |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 20GB | 100GB+ SSD |
| 网络 | 100Mbps | 1Gbps |

### 2. 备份策略

```bash
# 数据备份脚本
#!/bin/bash
BACKUP_DIR="/backup/ai-codereview"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
cp ./data/data.db "$BACKUP_DIR/data_$DATE.db"

# 备份配置文件
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" ./conf/

# 备份日志文件
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" ./log/
```

### 3. 更新策略

```bash
# 更新脚本
#!/bin/bash
# 停止服务
docker-compose down

# 备份数据
./backup.sh

# 拉取最新镜像
docker-compose pull

# 启动服务
docker-compose up -d

# 检查服务状态
docker-compose ps
```

## 🛠️ 故障排查

### 常见问题

1. **服务无法启动**
```bash
# 检查日志
docker-compose logs app

# 检查配置文件
cat conf/.env

# 检查端口占用
netstat -tulpn | grep 5001
```

2. **数据库连接问题**
```bash
# 检查数据库文件权限
ls -la data/data.db

# 重置数据库
rm data/data.db
docker-compose restart app
```

3. **Webhook 不工作**
```bash
# 检查网络连通
curl -X POST http://your-domain.com/api/webhook/gitlab

# 检查配置
grep WEBHOOK conf/.env
```

## 📞 技术支持

- **GitHub Issues**: https://github.com/zhao-zg/ai-codereview-gitlab/issues
- **文档**: https://github.com/zhao-zg/ai-codereview-gitlab/blob/main/README.md
- **Docker Hub**: https://hub.docker.com/r/zzg1189/ai-codereview-gitlab

---

*本部署指南涵盖了从基础部署到生产环境的完整配置，如有问题请提交 Issue 或查阅 FAQ 文档。*
