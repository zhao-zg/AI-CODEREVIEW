# Docker Compose 快速使用指南

这是 AI-CodeReview 项目的 Docker Compose 快速使用指南。

## 🚀 快速开始

### 1. 准备环境变量文件

```bash
# 复制环境变量示例文件
cp .env.docker.example .env

# 编辑环境变量文件
# 必须配置的变量：
# - LLM_PROVIDER: 选择 AI 提供商 (deepseek/openai/zhipuai/qwen)
# - API_KEY: 对应的 API 密钥
# - DASHBOARD_PASSWORD: 仪表板访问密码
```

### 2. 启动服务

```bash
# 仅启动基础服务（API + UI）
docker-compose up -d

# 启动所有服务（包括后台队列处理）
COMPOSE_PROFILES=worker docker-compose up -d
```

### 3. 访问服务

- **API 服务**：http://localhost:5001
- **Web UI**：http://localhost:5002
- **健康检查**：http://localhost:5001/health

## 📦 服务架构

### 基础服务
- **ai-codereview**: 主应用服务，包含 API 和 Web UI
  - 端口：5001 (API), 5002 (UI)
  - 数据持久化：`./conf`, `./data`, `./log`

### 可选服务（需要 COMPOSE_PROFILES=worker）
- **ai-codereview-worker**: 后台任务处理服务
- **redis**: 队列存储和缓存服务

## ⚙️ 配置管理

### 环境变量配置
主要通过 `.env` 文件配置，支持的变量：

```bash
# 镜像和容器配置
DOCKER_IMAGE=ghcr.io/zhao-zg/ai-codereview
IMAGE_TAG=latest
CONTAINER_NAME_PREFIX=ai-codereview

# 端口配置
API_PORT=5001
UI_PORT=5002

# 基础配置
TZ=Asia/Shanghai
LOG_LEVEL=INFO

# AI 服务配置
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key_here

# 应用配置
DASHBOARD_PASSWORD=your_password
```

### 配置文件自动初始化
容器启动时会自动：
1. 检测 `conf` 目录配置文件完整性
2. 从模板自动创建缺失的配置文件
3. 初始化环境变量和应用配置

## 🔧 常用命令

### 服务管理
```bash
# 启动服务
docker-compose up -d

# 启动带 worker 的完整服务
COMPOSE_PROFILES=worker docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f ai-codereview
```

### 配置验证
```bash
# 验证配置文件语法
docker-compose config

# 验证带 worker 的配置
COMPOSE_PROFILES=worker docker-compose config
```

### 数据管理
```bash
# 备份数据
docker-compose exec ai-codereview tar -czf /tmp/backup.tar.gz /app/data /app/conf

# 清理数据（谨慎操作）
docker-compose down -v
```

## 🐛 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 查看详细日志
   docker-compose logs ai-codereview
   
   # 检查配置文件
   docker-compose config
   ```

2. **端口冲突**
   ```bash
   # 修改 .env 文件中的端口配置
   API_PORT=5003
   UI_PORT=5004
   ```

3. **配置文件问题**
   ```bash
   # 重新初始化配置
   docker-compose exec ai-codereview python /app/scripts/docker_init.py
   ```

4. **权限问题**
   ```bash
   # 确保目录权限正确
   sudo chown -R $(id -u):$(id -g) ./conf ./data ./log
   ```

### 健康检查

服务提供了健康检查端点：
- **API 健康检查**：`GET /health`
- **服务状态**：`docker-compose ps`

## 📁 目录结构

```
AI-CodeReview/
├── docker-compose.yml          # 主配置文件
├── .env.docker.example         # 环境变量示例
├── .env                       # 实际环境变量（需要创建）
├── conf/                      # 配置文件目录（自动映射）
├── data/                      # 数据目录（持久化）
├── log/                       # 日志目录（持久化）
└── scripts/docker_init.py     # 配置初始化脚本
```

## 🔄 更新和维护

### 更新镜像
```bash
# 拉取最新镜像
docker-compose pull

# 重新启动服务
docker-compose up -d
```

### 定期维护
```bash
# 清理未使用的资源
docker system prune -f

# 备份重要数据
docker-compose exec ai-codereview tar -czf /app/backup-$(date +%Y%m%d).tar.gz /app/data
```

## 🚨 安全建议

1. **修改默认密码**：确保修改 `DASHBOARD_PASSWORD`
2. **API 密钥安全**：不要在代码中硬编码 API 密钥
3. **网络安全**：生产环境建议使用反向代理
4. **数据备份**：定期备份 `data` 和 `conf` 目录

## 📞 获取帮助

如果遇到问题，请：
1. 查看日志：`docker-compose logs -f`
2. 检查配置：`docker-compose config`
3. 提交 Issue 或查看文档
