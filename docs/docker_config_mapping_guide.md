# Docker 配置文件自动复制指南

## 🎯 概述

AI-CodeReview 项目现在支持 Docker 配置文件的智能自动复制和管理。通过映射 `conf` 目录，您可以实现配置的持久化和灵活管理。

## 🔧 核心机制

### 1. 自动配置初始化

容器启动时，会自动执行 `scripts/docker_init.py` 脚本，该脚本会：

- ✅ **检查必要配置文件** - 确保所有必需的配置文件都存在
- ✅ **自动创建默认配置** - 从 `.env.dist` 创建 `.env` 文件（如果不存在）
- ✅ **加载环境变量** - 自动加载 `.env` 文件中的配置
- ✅ **配置 supervisord** - 根据运行模式自动选择正确的 supervisord 配置
- ✅ **验证关键配置** - 检查重要配置项是否正确设置

### 2. 配置文件映射

通过在 Docker Compose 中映射 `conf` 目录：

```yaml
volumes:
  - ./conf:/app/conf
```

可以实现：
- 📁 **配置持久化** - 配置更改在容器重启后保留
- 🔄 **双向同步** - 主机和容器间的配置文件自动同步
- ⚙️ **灵活管理** - 可以直接在主机上编辑配置文件

## 🚀 使用方法

### 方式一：使用 Docker Compose（推荐）

1. **复制示例配置**
   ```bash
   cp docker-compose.example.yml docker-compose.yml
   ```

2. **创建配置目录**
   ```bash
   mkdir -p conf data log
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

### 方式二：使用 Docker 命令

```bash
# 创建配置目录
mkdir -p conf data log

# 运行应用容器
docker run -d \
  --name ai-codereview \
  -p 5001:5001 -p 5002:5002 \
  -v $(pwd)/conf:/app/conf \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  -e DOCKER_RUN_MODE=app \
  ai-codereview:latest
```

## 📁 配置文件结构

映射后的 `conf` 目录包含以下重要文件：

```
conf/
├── .env                      # 环境变量配置（自动创建）
├── .env.dist                 # 环境变量模板（内置默认值）
├── dashboard_config.py       # 仪表板配置
├── prompt_templates.yml      # AI 提示模板配置
├── supervisord.app.conf      # 应用服务配置
└── supervisord.worker.conf   # 工作服务配置
```

## ⚙️ 配置优先级

配置值的加载优先级（从高到低）：

1. **Docker 环境变量** - 通过 `-e` 参数或 `environment` 配置的变量
2. **conf/.env 文件** - 映射目录中的环境配置文件
3. **conf_templates/.env.dist** - 内置的默认配置模板
4. **代码默认值** - 程序中的备用默认值

## 🔍 配置验证

容器启动时会自动验证以下关键配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_PROVIDER` | 大语言模型提供商 | `deepseek` |
| `SERVER_PORT` | 服务端口 | `5001` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DASHBOARD_USER` | 仪表板用户名 | `admin` |
| `DASHBOARD_PASSWORD` | 仪表板密码 | `admin` |

## 💡 最佳实践

### 1. 配置文件管理

```bash
# 第一次启动后，配置文件会自动创建
docker-compose up -d

# 停止服务
docker-compose down

# 编辑配置文件
vim conf/.env

# 重启服务应用新配置
docker-compose up -d
```

### 2. 安全配置

```bash
# 设置适当的文件权限
chmod 600 conf/.env

# 不要将 .env 文件提交到版本控制
echo "conf/.env" >> .gitignore
```

### 3. 备份和恢复

```bash
# 备份配置
tar -czf config-backup-$(date +%Y%m%d).tar.gz conf/

# 恢复配置
tar -xzf config-backup-20241225.tar.gz
```

## 🐛 故障排除

### 问题 1：配置文件不存在

**症状**：容器启动失败，提示配置文件缺失

**解决方案**：
```bash
# 检查映射目录权限
ls -la conf/

# 重新初始化配置
docker run --rm -v $(pwd)/conf:/app/conf ai-codereview:latest python /app/scripts/init_env.py
```

### 问题 2：配置更改不生效

**症状**：修改 `.env` 文件后配置没有生效

**解决方案**：
```bash
# 重启容器以应用新配置
docker-compose restart

# 或者强制重新创建容器
docker-compose up -d --force-recreate
```

### 问题 3：权限问题

**症状**：容器无法创建或读取配置文件

**解决方案**：
```bash
# 设置正确的目录权限
sudo chown -R $(id -u):$(id -g) conf/ data/ log/
chmod -R 755 conf/ data/ log/
```

## 🔧 高级配置

### 自定义配置模板

您可以修改 `conf_templates/.env.dist` 来定制默认配置：

```bash
# 编辑模板文件
vim conf_templates/.env.dist

# 重新生成配置文件
rm conf/.env
docker-compose restart
```

### 多环境部署

```yaml
# 开发环境
version: '3.8'
services:
  ai-codereview-dev:
    build: .
    volumes:
      - ./conf/dev:/app/conf
    environment:
      - LOG_LEVEL=DEBUG

# 生产环境
version: '3.8'
services:
  ai-codereview-prod:
    image: ai-codereview:latest
    volumes:
      - ./conf/prod:/app/conf
    environment:
      - LOG_LEVEL=INFO
```

## 📊 监控和日志

### 查看配置初始化日志

```bash
# 查看容器启动日志
docker-compose logs ai-codereview

# 实时跟踪日志
docker-compose logs -f ai-codereview
```

### 配置变更审计

```bash
# 查看配置文件修改历史
git log --oneline conf/.env

# 比较配置差异
diff conf/.env conf_templates/.env.dist
```

## 🎉 总结

通过映射 `conf` 目录，AI-CodeReview 现在提供了：

- 🔄 **自动配置复制** - 必要文件自动创建和复制
- 📁 **配置持久化** - 配置在容器重启后保留
- ⚙️ **灵活管理** - 支持外部配置文件编辑
- 🛡️ **安全可靠** - 配置验证和错误处理
- 📊 **完整监控** - 详细的启动日志和状态检查

这种设计确保了 Docker 部署的便利性和配置管理的灵活性，适合各种部署场景。
