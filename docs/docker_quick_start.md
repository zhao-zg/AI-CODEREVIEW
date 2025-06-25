# Docker 部署快速参考

## 🚀 一键启动（推荐）

```bash
# Linux/Mac
./start.sh

# Windows  
start.bat
```

## � 手动部署命令

### 多容器模式（推荐生产环境）

```bash
# 基础模式（仅 API + UI）
docker-compose up -d

# 完整模式（API + UI + Worker + Redis）
COMPOSE_PROFILES=worker docker-compose up -d

# 检查服务状态
docker-compose ps
```

### 单容器模式（开发/测试）

```bash
# 基础模式
docker-compose -f docker-compose.single.yml up -d

# 包含 Redis
COMPOSE_PROFILES=redis docker-compose -f docker-compose.single.yml up -d
```

## 🔧 环境配置

```bash
# 复制配置模板
cp .env.docker.example .env

# 关键配置项
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key
COMPOSE_PROFILES=worker  # 启用 worker 服务
QUEUE_DRIVER=rq          # 多容器推荐 rq，单容器推荐 process
```

## 🧪 测试验证

```bash
# 测试多容器配置
python test_multi_container.py

# 测试单容器配置  
python test_single_container.py

# 检查配置语法
docker-compose config --quiet
```

## 📊 服务访问

- **API**: http://localhost:5001
- **UI**: http://localhost:5002

## 🛠️ 常用操作

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 强制重建
docker-compose up -d --build --force-recreate
```

## 🔄 模式切换

### 从单容器切换到多容器

```bash
# 停止单容器
docker-compose -f docker-compose.single.yml down

# 启动多容器（完整模式）
COMPOSE_PROFILES=worker docker-compose up -d
```

### 从多容器切换到单容器

```bash  
# 停止多容器
docker-compose down

# 启动单容器
docker-compose -f docker-compose.single.yml up -d
```

## ⚠️ 注意事项

1. **数据持久化**：`./data`、`./log`、`./conf` 目录会自动映射
2. **端口冲突**：确保 5001、5002 端口未被占用
3. **资源要求**：多容器模式需要更多内存（推荐 2GB+）
4. **网络配置**：默认使用 `172.20.0.0/16` 子网

## 🚨 故障排除

```bash
# 检查容器状态
docker ps -a

# 查看详细日志
docker-compose logs [service_name]

# 检查网络连接
docker network ls
docker network inspect ai-codereview-network

# 重置环境
docker-compose down -v
docker system prune -f
```

# 启动服务
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

### 3️⃣ 配置验证

```bash
# 检查服务状态
docker-compose ps

# 访问服务
# API: http://localhost:5001
# UI:  http://localhost:5002
```

## 📁 配置文件自动复制说明

### 自动复制的配置文件

当您映射 `./conf:/app/conf` 后，以下配置文件会自动创建和管理：

| 文件名 | 说明 | 自动创建 |
|--------|------|----------|
| `.env` | 环境变量配置 | ✅ 从 .env.dist 复制 |
| `.env.dist` | 配置模板 | ✅ 内置在镜像中 |
| `dashboard_config.py` | 仪表板配置 | ✅ 内置在镜像中 |
| `prompt_templates.yml` | AI 提示模板 | ✅ 内置在镜像中 |
| `supervisord.app.conf` | 应用服务配置 | ✅ 内置在镜像中 |
| `supervisord.worker.conf` | 工作服务配置 | ✅ 内置在镜像中 |

### 初始化流程

1. **检查配置文件** - 验证所有必要文件是否存在
2. **自动创建缺失文件** - 从内置模板复制到映射目录
3. **生成默认 .env** - 如果 .env 不存在，从 .env.dist 创建
4. **加载环境变量** - 自动读取 .env 文件中的配置
5. **配置服务** - 根据运行模式配置 supervisord
6. **验证配置** - 检查关键配置项

## 🔧 配置管理

### 编辑配置

```bash
# 停止服务
docker-compose down

# 编辑主配置文件
vim conf/.env

# 重启服务
docker-compose up -d
```

### 重置配置

```bash
# 删除现有配置
rm -f conf/.env

# 重启容器，会自动重新创建默认配置
docker-compose restart
```

### 备份配置

```bash
# 备份整个配置目录
tar -czf config-backup-$(date +%Y%m%d).tar.gz conf/

# 恢复配置
tar -xzf config-backup-20241225.tar.gz
```

## 🎯 核心特性

✅ **自动配置初始化** - 容器启动时自动创建所有必要配置文件  
✅ **配置持久化** - 通过目录映射保证配置在容器重启后保留  
✅ **双向同步** - 主机和容器间配置文件实时同步  
✅ **智能默认值** - 从 .env.dist 自动生成合理的默认配置  
✅ **灵活覆盖** - 支持通过环境变量覆盖配置文件中的值  
✅ **错误处理** - 配置验证和友好的错误提示  

## 🔍 故障排除

### 配置文件权限问题

```bash
# 设置正确权限
sudo chown -R $(id -u):$(id -g) conf/ data/ log/
chmod -R 755 conf/ data/ log/
chmod 600 conf/.env  # 保护敏感配置
```

### 配置不生效

```bash
# 检查配置文件语法
cat conf/.env | grep -v "^#" | grep "="

# 强制重新创建容器
docker-compose up -d --force-recreate
```

### 查看详细日志

```bash
# 查看初始化日志
docker-compose logs ai-codereview | grep "Docker 配置"

# 查看运行时日志
docker-compose logs -f ai-codereview
```

## 💡 最佳实践

1. **首次启动前** - 创建配置目录并设置适当权限
2. **配置管理** - 定期备份 conf 目录
3. **安全考虑** - 不要将 .env 文件提交到版本控制
4. **监控** - 定期检查配置验证日志
5. **更新** - 配置更改后重启容器使其生效

通过这种设计，您可以轻松地管理 AI-CodeReview 的配置，实现真正的"一键部署"体验！
