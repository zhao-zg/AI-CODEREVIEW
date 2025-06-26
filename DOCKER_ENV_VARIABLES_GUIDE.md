# Docker 环境变量配置说明

## 🔍 环境变量设置层级

### 1. Dockerfile (镜像默认值)
```dockerfile
# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING=utf-8
ENV DOCKER_ENV=true
```

**作用**：为镜像设置默认环境变量，确保基础功能正常。

### 2. Docker Compose (运行时覆盖)
```yaml
environment:
  # Python 输出配置（覆盖 Dockerfile 中的默认值）
  - PYTHONUNBUFFERED=1
  - PYTHONDONTWRITEBYTECODE=1
  - PYTHONIOENCODING=utf-8
  
  # Docker 环境标识（覆盖 Dockerfile 默认值）
  - DOCKER_ENV=true
  
  # 运行时特定配置
  - LOG_LEVEL=INFO
  - LOG_FILE=log/app.log
```

**作用**：运行时配置，可以覆盖镜像默认值，便于不同环境的配置。

### 3. 启动脚本 (显示状态)
```bash
# 显示环境变量状态（ENV已设置，无需重复export）
echo "🔧 Python环境: PYTHONUNBUFFERED=${PYTHONUNBUFFERED}"
echo "🔧 字符编码: PYTHONIOENCODING=${PYTHONIOENCODING}"
echo "🔧 Docker环境: DOCKER_ENV=${DOCKER_ENV}"
```

**作用**：显示当前生效的环境变量值，便于调试。

## ✅ 优化改进

### 🔧 **修复前的问题**：
```bash
# Dockerfile 中设置
ENV PYTHONUNBUFFERED=1

# 启动脚本中重复设置
export PYTHONUNBUFFERED=1  # ❌ 重复设置
```

### ✅ **修复后的结果**：
```bash
# Dockerfile 中设置（镜像默认值）
ENV PYTHONUNBUFFERED=1

# 启动脚本中只显示状态（不重复设置）
echo "🔧 Python环境: PYTHONUNBUFFERED=${PYTHONUNBUFFERED}"  # ✅ 只显示状态
```

## 📋 环境变量说明

| 变量名 | 设置位置 | 作用 | 必要性 |
|--------|----------|------|--------|
| `PYTHONUNBUFFERED=1` | Dockerfile + Compose | 禁用 Python 输出缓冲，确保实时日志 | ⭐⭐⭐ |
| `PYTHONDONTWRITEBYTECODE=1` | Dockerfile + Compose | 禁用 .pyc 文件生成，减少容器体积 | ⭐⭐ |
| `PYTHONIOENCODING=utf-8` | Dockerfile + Compose | 强制 UTF-8 编码，避免中文乱码 | ⭐⭐⭐ |
| `DOCKER_ENV=true` | Dockerfile + Compose | 标识 Docker 环境，调整应用行为 | ⭐⭐ |
| `LOG_LEVEL=INFO` | Compose only | 运行时日志级别控制 | ⭐⭐ |
| `LOG_FILE=log/app.log` | Compose only | 运行时日志文件路径 | ⭐ |

## 🎯 最佳实践

1. **镜像默认值**：在 Dockerfile 中设置基础必需的环境变量
2. **运行时覆盖**：在 Docker Compose 中设置可变的配置
3. **避免重复**：不在启动脚本中重复 export 已设置的环境变量
4. **状态显示**：在启动脚本中显示关键环境变量的值，便于调试

## 🔄 环境变量优先级

```
Docker Compose environment > Dockerfile ENV > 系统默认
```

这样的设计既保证了镜像的可用性，又提供了运行时的灵活性。
