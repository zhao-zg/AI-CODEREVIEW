# 配置说明

## 🎯 配置文件位置

由于不再依赖 .env 文件，所有配置都已内置在 Docker Compose 文件中：

- **多容器配置**: `docker-compose.yml`
- **单容器配置**: `docker-compose.single.yml`

## 🔧 自定义配置

如果需要修改默认配置，可以直接编辑对应的 docker-compose 文件：

### 常见配置项

1. **端口配置**
   ```yaml
   ports:
     - "5001:5001"  # API 端口
     - "5002:5002"  # UI 端口
   ```

2. **环境变量**
   ```yaml
   environment:
     - TZ=Asia/Shanghai
     - LOG_LEVEL=INFO
     - PYTHON_ENV=production
   ```

3. **数据目录**
   ```yaml
   volumes:
     - ./conf:/app/conf
     - ./data:/app/data
     - ./log:/app/log
     - ./data/svn:/app/data/svn
   ```

## 🚀 LLM API 配置

如需配置 LLM API 密钥，可以通过以下方式：

### 方法一：修改 docker-compose 文件（推荐）

在 `environment` 部分添加：
```yaml
environment:
  - LLM_PROVIDER=deepseek
  - DEEPSEEK_API_KEY=your_api_key_here
  - OPENAI_API_KEY=your_openai_key_here
  # 其他配置...
```

### 方法二：使用环境变量启动

```bash
# 设置环境变量
export DEEPSEEK_API_KEY=your_api_key_here
export LLM_PROVIDER=deepseek

# 启动服务
docker-compose up -d
```

### 方法三：创建 .env 文件（可选）

如果您偏好使用 .env 文件，可以创建并设置：
```bash
# 复制示例文件
cp .env.docker.example .env

# 编辑配置
nano .env
```

## 📊 配置验证

运行测试脚本验证配置：
```bash
# 测试多容器配置
python test_multi_container.py

# 测试单容器配置
python test_single_container.py
```

## 🔄 部署模式对比

| 配置项 | 多容器模式 | 单容器模式 |
|--------|------------|------------|
| 文件 | docker-compose.yml | docker-compose.single.yml |
| 容器数量 | 2-3个 | 1-2个 |
| 队列类型 | RQ (Redis) | Process |
| 适用场景 | 生产环境 | 开发测试 |
| 资源要求 | 中等 | 较低 |
| 扩展性 | 高 | 低 |
