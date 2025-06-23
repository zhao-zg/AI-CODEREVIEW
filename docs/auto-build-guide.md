# 自动化构建和发布指南

本文档介绍如何使用已配置的GitHub Actions自动构建和发布Docker镜像。

## 🚀 自动触发构建

### 推送代码自动构建

当你向以下分支推送代码时，会自动触发Docker镜像构建：

```bash
git push origin main      # 推送到main分支
git push origin master    # 推送到master分支  
git push origin develop   # 推送到develop分支
```

### 创建标签自动发布

当你创建版本标签时，会自动构建并发布带版本号的镜像：

```bash
# 使用发布脚本（推荐）
python scripts/release.py --increment patch

# 或手动创建标签
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

## 🛠️ 使用脚本管理发布

### 1. 本地测试Docker构建

在提交代码前，先本地测试构建：

```bash
# 完整测试（构建+运行测试）
python scripts/test_docker_local.py

# 仅构建测试
python scripts/test_docker_local.py --build-only

# 仅运行测试（需要先构建）
python scripts/test_docker_local.py --test-only

# 清理测试镜像
python scripts/test_docker_local.py --cleanup
```

### 2. 版本发布

使用发布脚本创建新版本：

```bash
# 自动递增patch版本（1.2.3 -> 1.2.4）
python scripts/release.py

# 递增minor版本（1.2.3 -> 1.3.0）
python scripts/release.py --increment minor

# 递增major版本（1.2.3 -> 2.0.0）
python scripts/release.py --increment major

# 指定版本号
python scripts/release.py --version 2.1.0

# 预览模式（不实际创建）
python scripts/release.py --dry-run

# 跳过GitHub Release创建
python scripts/release.py --skip-github-release
```

### 3. 检查构建状态

监控GitHub Actions和Docker镜像状态：

```bash
# 检查CI状态和镜像
python scripts/check_ci_status.py

# 只检查CI状态
python scripts/check_ci_status.py --check-ci

# 只检查镜像状态
python scripts/check_ci_status.py --check-image

# 检查本地Docker环境
python scripts/check_ci_status.py --check-local

# 手动触发构建（需要GitHub CLI）
python scripts/check_ci_status.py --trigger-build
```

## 📦 Docker镜像说明

### 镜像类型

系统会自动构建两种镜像：

1. **应用镜像** (`app`): 包含Web UI和API服务
   - `ghcr.io/zhao-zg/ai-codereview-gitlab:latest`
   - `ghcr.io/zhao-zg/ai-codereview-gitlab:v1.2.3`

2. **工作镜像** (`worker`): 包含后台处理服务
   - `ghcr.io/zhao-zg/ai-codereview-gitlab:latest-worker`
   - `ghcr.io/zhao-zg/ai-codereview-gitlab:v1.2.3-worker`

### 支持的平台

- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)

### 使用镜像

```bash
# 拉取最新镜像
docker pull ghcr.io/zhao-zg/ai-codereview-gitlab:latest
docker pull ghcr.io/zhao-zg/ai-codereview-gitlab:latest-worker

# 使用docker-compose运行
docker-compose up -d

# 或单独运行应用容器
docker run -d -p 5001:5001 -p 5002:5002 \
  -v ./data:/app/data \
  -v ./log:/app/log \
  --env-file ./conf/.env \
  ghcr.io/zhao-zg/ai-codereview-gitlab:latest
```

## 🔧 GitHub Actions工作流

### 主要工作流

1. **docker-build.yml**: Docker镜像构建和发布
2. **test.yml**: 代码测试
3. **release.yml**: 版本发布
4. **update-deps.yml**: 依赖更新（定时任务）

### 触发条件

| 工作流 | 触发条件 | 说明 |
|--------|----------|------|
| docker-build | push到main/master/develop分支<br>创建v*.*.*标签<br>PR到main/master | 构建并发布Docker镜像 |
| test | push到任何分支<br>创建PR | 运行代码测试 |
| release | 创建v*.*.*标签 | 创建GitHub Release |
| update-deps | 每周定时<br>手动触发 | 更新Python依赖 |

### 查看构建状态

1. **GitHub网页**: https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB/actions
2. **命令行**: `python scripts/check_ci_status.py`
3. **GitHub CLI**: `gh run list`

## 🔐 权限和认证

### GitHub Actions权限

工作流已配置必要的权限：
- `contents: read` - 读取仓库内容
- `packages: write` - 写入容器包
- `actions: read` - 读取Actions信息

### Docker镜像访问

- **公开访问**: 镜像是公开的，任何人都可以拉取
- **推送权限**: 只有仓库协作者可以推送新镜像

## 🚨 故障排除

### 构建失败

1. **检查GitHub Actions日志**:
   ```bash
   # 使用脚本检查
   python scripts/check_ci_status.py --check-ci
   
   # 或访问网页
   # https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB/actions
   ```

2. **本地复现问题**:
   ```bash
   # 本地测试构建
   python scripts/test_docker_local.py
   
   # 手动构建
   docker build --target app -t test-app .
   docker build --target worker -t test-worker .
   ```

3. **常见问题**:
   - **依赖安装失败**: 检查`requirements.txt`
   - **文件路径错误**: 检查`.dockerignore`和文件复制路径
   - **权限问题**: 检查GitHub仓库设置中的Actions权限

### 镜像拉取失败

1. **检查镜像是否存在**:
   ```bash
   python scripts/check_ci_status.py --check-image
   ```

2. **手动拉取测试**:
   ```bash
   docker pull ghcr.io/zhao-zg/ai-codereview-gitlab:latest
   ```

3. **检查网络和认证**:
   ```bash
   # 登录GitHub Container Registry（如果需要）
   echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
   ```

## 📝 最佳实践

### 开发流程

1. **本地开发**:
   ```bash
   # 开发代码
   # 本地测试
   python scripts/test_docker_local.py
   ```

2. **提交代码**:
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   git push origin develop  # 会触发构建测试
   ```

3. **合并到主分支**:
   ```bash
   git checkout main
   git merge develop
   git push origin main  # 会构建并发布latest镜像
   ```

4. **发布版本**:
   ```bash
   python scripts/release.py  # 创建版本标签和Release
   ```

### 版本管理

- 使用语义化版本号（Semantic Versioning）
- 主要功能更新递增minor版本
- Bug修复递增patch版本
- 重大变更递增major版本

### 镜像管理

- `latest`标签总是指向main分支的最新构建
- 使用具体版本号标签进行生产部署
- 定期清理旧的镜像版本（GitHub会自动管理）

## 🔗 相关链接

- [GitHub Actions文档](https://docs.github.com/en/actions)
- [GitHub Container Registry文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker多阶段构建](https://docs.docker.com/develop/dev-best-practices/dockerfile_best-practices/#use-multi-stage-builds)
- [语义化版本](https://semver.org/lang/zh-CN/)
