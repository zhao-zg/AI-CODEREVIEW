# GitHub Actions CI/CD 配置指南

## 📋 概述

为AI代码审查系统配置了完整的GitHub Actions CI/CD流水线，支持自动化构建、测试、安全扫描和Docker镜像发布。

## 🚀 工作流说明

### 1. 主构建工作流 (`docker-build.yml`)

**触发条件:**
- 推送到 `main`、`master`、`develop` 分支
- 创建 Pull Request 到 `main`、`master` 分支
- 推送版本标签 (`v*.*.*`)

**功能:**
- 🐳 自动构建Docker镜像（app和worker）
- 📦 发布到GitHub Container Registry (ghcr.io)
- 🏗️ 支持多架构构建 (linux/amd64, linux/arm64)
- ⚡ 使用GitHub Actions缓存加速构建

**生成的镜像:**
- `ghcr.io/用户名/仓库名:latest` (主应用)
- `ghcr.io/用户名/仓库名:latest-worker` (工作进程)

### 2. 发布工作流 (`release.yml`)

**触发条件:**
- 推送版本标签 (`v*.*.*`)

**功能:**
- 🏷️ 自动创建GitHub Release
- 📝 从CHANGELOG.md提取发布说明
- 🐳 构建并发布带版本号的Docker镜像
- 📋 支持语义化版本标签

**镜像标签示例:**
```
ghcr.io/用户名/仓库名:v1.4.0
ghcr.io/用户名/仓库名:v1.4
ghcr.io/用户名/仓库名:v1
ghcr.io/用户名/仓库名:latest
ghcr.io/用户名/仓库名:v1.4.0-worker
```

### 3. 测试工作流 (`test.yml`)

**触发条件:**
- 推送到主分支
- 创建Pull Request

**功能:**
- 🐍 多Python版本测试 (3.9, 3.10, 3.11)
- 🔍 代码质量检查 (flake8)
- 🧪 自动化测试 (pytest)
- 🐳 Docker构建验证
- 🔒 安全漏洞扫描 (Trivy)

### 4. 依赖更新工作流 (`update-deps.yml`)

**触发条件:**
- 每周一自动运行
- 手动触发

**功能:**
- 📦 自动更新Python依赖
- 🔄 创建更新Pull Request
- ⚡ 使用pip-tools管理依赖

## 🔧 设置步骤

### 1. 仓库设置

确保GitHub仓库有以下设置：

```bash
# 仓库权限
Settings -> Actions -> General
- Actions permissions: Allow all actions
- Workflow permissions: Read and write permissions
```

### 2. Container Registry权限

GitHub Container Registry会自动配置，但需要确保：

```bash
# 包权限
Settings -> Actions -> General -> Workflow permissions
✅ Read and write permissions
✅ Allow GitHub Actions to create and approve pull requests
```

### 3. 分支保护（可选）

```bash
Settings -> Branches -> Add rule
- Branch name pattern: main
- Require status checks to pass before merging
- Require pull request reviews before merging
```

## 📦 使用Docker镜像

### 拉取最新镜像

```bash
# 拉取主应用镜像
docker pull ghcr.io/用户名/ai-codereview-gitlab:latest

# 拉取工作进程镜像
docker pull ghcr.io/用户名/ai-codereview-gitlab:latest-worker
```

### 使用特定版本

```bash
# 使用特定版本
docker pull ghcr.io/用户名/ai-codereview-gitlab:v1.4.0
docker pull ghcr.io/用户名/ai-codereview-gitlab:v1.4.0-worker
```

### Docker Compose配置

```yaml
services:
  app:
    image: ghcr.io/用户名/ai-codereview-gitlab:latest
    # ... 其他配置
  
  worker:
    image: ghcr.io/用户名/ai-codereview-gitlab:latest-worker
    # ... 其他配置
```

## 🏷️ 版本发布流程

### 1. 创建版本标签

```bash
# 创建并推送版本标签
git tag v1.4.0
git push origin v1.4.0
```

### 2. 自动化流程

1. GitHub Actions检测到标签推送
2. 自动构建Docker镜像
3. 发布到Container Registry
4. 创建GitHub Release
5. 生成发布说明

### 3. 更新docker-compose.yml

发布后，更新本地配置：

```yaml
services:
  app:
    image: ghcr.io/zhaozhenggang/ai-codereview-gitlab:v1.4.0
```

## 📊 工作流状态

可以在仓库的Actions标签页查看：

- ✅ **成功**: 所有检查通过，镜像已发布
- ❌ **失败**: 构建或测试失败，需要修复
- 🟡 **进行中**: 工作流正在运行

## 🔒 安全特性

### 1. 自动安全扫描
- 使用Trivy扫描代码和依赖漏洞
- 结果上传到GitHub Security标签页

### 2. 权限最小化
- 使用GitHub内置的GITHUB_TOKEN
- 限制工作流权限范围

### 3. 多架构支持
- 支持AMD64和ARM64架构
- 提高部署兼容性

## 🚀 优化特性

### 1. 构建缓存
- 使用GitHub Actions缓存
- 显著减少构建时间

### 2. 并行构建
- app和worker镜像并行构建
- 多Python版本并行测试

### 3. 智能触发
- 仅在相关代码变更时触发
- 避免不必要的构建

## 📋 故障排除

### 常见问题

1. **权限错误**
   ```
   Error: failed to solve: failed to push to ghcr.io
   ```
   解决：检查仓库的Actions权限设置

2. **构建失败**
   ```
   Error: failed to build
   ```
   解决：检查Dockerfile和依赖文件

3. **测试失败**
   ```
   Error: tests failed
   ```
   解决：修复代码后重新推送

### 日志查看

在GitHub仓库的Actions页面可以查看详细的构建日志和错误信息。

---

**总结**: GitHub Actions CI/CD流水线已配置完成，支持自动化构建、测试和发布Docker镜像。推送代码到GitHub后，系统会自动构建并发布到ghcr.io，大大简化了部署流程。
