# AI-CodeReview 单容器部署指南

## 🎯 概述

新版本的 Docker Compose 配置支持在单个容器中运行所有服务，包括：
- 🌐 Flask API 服务 (端口 5001)
- 🎨 Streamlit Web UI (端口 5002)  
- ⚙️ 后台任务处理器 (可选)
- 📊 SVN 定时检查 (可选)

## 🚀 快速开始

### 1. 基础部署（推荐）

```bash
# 复制环境变量配置文件
cp .env.docker.example .env

# 启动单容器服务
docker-compose up -d
```

这将启动一个包含所有功能的容器：
- ✅ API 和 Web UI 服务
- ✅ 后台任务处理器（进程模式）
- ✅ 支持 GitLab/GitHub Webhook
- ✅ 支持 SVN 定时检查（如果启用）

### 2. 高性能部署（使用 Redis 队列）

如果需要处理大量并发请求，可以启用 Redis 队列模式：

```bash
# 编辑 .env 文件
QUEUE_DRIVER=rq
COMPOSE_PROFILES=redis

# 启动服务（包含 Redis）
docker-compose --profile redis up -d
```

## ⚙️ 配置选项

### 核心配置

```bash
# 基础服务配置
API_PORT=5001                    # API 服务端口
UI_PORT=5002                     # Web UI 端口
CONTAINER_NAME_PREFIX=ai-codereview  # 容器名前缀

# 后台任务配置
ENABLE_WORKER=true               # 是否启用后台任务处理器
QUEUE_DRIVER=process             # 队列模式: process 或 rq

# SVN 配置
SVN_CHECK_ENABLED=false          # 是否启用 SVN 定时检查
SVN_CHECK_INTERVAL=300           # SVN 检查间隔（秒）
```

### 队列模式对比

| 模式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **process** | 简单、无需 Redis | 并发能力有限 | 小团队、轻量使用 |
| **rq** | 高并发、可扩展 | 需要 Redis 服务 | 大团队、高并发 |

## 📁 目录结构

```
AI-CodeReview/
├── docker-compose.yml              # 单容器配置（主配置）
├── docker-compose.single.yml       # 单容器配置（备用）
├── .env.docker.example             # 环境变量示例
├── .env                            # 实际环境变量
├── conf/
│   ├── supervisord.app.conf        # 仅 API + UI
│   ├── supervisord.worker.conf     # 仅后台任务
│   └── supervisord.all.conf        # 所有服务 (新增)
├── scripts/
│   ├── background_worker.py        # 后台任务处理器 (新增)
│   └── docker_init.py              # 配置初始化脚本
└── ...
```

## 🔧 高级配置

### 自定义后台任务

编辑 `.env` 文件：

```bash
# 启用特定功能
SVN_CHECK_ENABLED=true
SVN_CHECK_INTERVAL=600          # 10分钟检查一次

# LLM 配置
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key_here

# 通知配置
DASHBOARD_PASSWORD=your_password
```

### Redis 队列模式

启用高性能队列处理：

```bash
# .env 文件配置
QUEUE_DRIVER=rq
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_MAXMEMORY=512m

# 启动命令
COMPOSE_PROFILES=redis docker-compose up -d
```

## 🚀 启动脚本

### Windows 用户

```bash
# 一键启动
start.bat
```

### Linux/macOS 用户

```bash
# 一键启动
./start.sh
```

启动脚本会自动：
1. 检查 Docker 环境
2. 创建必要目录
3. 配置环境变量
4. 选择部署模式
5. 启动服务

## 📊 监控和日志

### 查看服务状态

```bash
# 查看容器状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f ai-codereview
```

### 健康检查

访问健康检查端点：
- API 健康检查: http://localhost:5001/health
- Web UI: http://localhost:5002

### 查看后台任务状态

```bash
# 进入容器
docker-compose exec ai-codereview bash

# 查看 supervisord 状态
supervisorctl status

# 重启后台任务
supervisorctl restart worker
```

## 🔄 维护操作

### 更新服务

```bash
# 拉取最新镜像
docker-compose pull

# 重新启动服务
docker-compose up -d
```

### 备份数据

```bash
# 备份数据和日志
docker-compose exec ai-codereview tar -czf /tmp/backup.tar.gz /app/data /app/log

# 复制到主机
docker cp $(docker-compose ps -q ai-codereview):/tmp/backup.tar.gz ./backup.tar.gz
```

### 清理资源

```bash
# 停止并删除容器
docker-compose down

# 删除数据卷（谨慎操作）
docker-compose down -v
```

## 🆚 对比旧版本

| 特性 | 旧版本 (多容器) | 新版本 (单容器) |
|------|----------------|----------------|
| 容器数量 | 3个 (app + worker + redis) | 1个 (或 2个含 redis) |
| 内存占用 | 高 | 低 |
| 启动时间 | 慢 | 快 |
| 配置复杂度 | 复杂 | 简单 |
| 扩展性 | 高 | 中等 |
| 适用场景 | 大型团队 | 中小型团队 |

## 🔧 故障排除

### 常见问题

1. **后台任务不工作**
   ```bash
   # 检查配置
   docker-compose exec ai-codereview env | grep ENABLE_WORKER
   
   # 查看任务状态
   docker-compose exec ai-codereview supervisorctl status worker
   ```

2. **SVN 检查失败**
   ```bash
   # 检查 SVN 配置
   docker-compose exec ai-codereview env | grep SVN_
   
   # 手动测试 SVN 连接
   docker-compose exec ai-codereview svn info YOUR_SVN_URL
   ```

3. **Redis 连接问题**
   ```bash
   # 确保启用了 Redis profile
   COMPOSE_PROFILES=redis docker-compose up -d
   
   # 测试 Redis 连接
   docker-compose exec redis redis-cli ping
   ```

## 📞 获取帮助

如果遇到问题：
1. 查看日志：`docker-compose logs -f`
2. 检查健康状态：`docker-compose ps`
3. 验证配置：`docker-compose config`
4. 重启服务：`docker-compose restart`

## 🎉 总结

新的单容器模式提供了：
- ✅ 更简单的部署
- ✅ 更少的资源占用  
- ✅ 更快的启动速度
- ✅ 保持所有功能完整

推荐中小型团队使用单容器模式，大型团队可以考虑使用 Redis 队列模式或传统的多容器部署。
