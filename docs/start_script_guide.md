# 启动脚本使用说明

## 🚀 新增功能

### 环境自动安装
启动脚本现在支持自动安装和配置：

#### Linux/Mac (`start.sh`)
- ✅ 自动检测操作系统类型
- ✅ 自动安装 Docker (Ubuntu/Debian/CentOS/macOS)
- ✅ 自动安装 Docker Compose
- ✅ 自动下载最新配置文件
- ✅ 智能环境检查和修复

#### Windows (`start.bat`)
- ✅ 自动检测 Docker 环境
- ✅ 引导下载 Docker Desktop
- ✅ 自动下载最新配置文件
- ✅ PowerShell 集成下载功能

### 配置文件自动下载
启动脚本会自动从 GitHub 仓库下载最新的配置文件：

- `docker-compose.yml` (多容器配置)
- `docker-compose.single.yml` (单容器配置)  
- `Dockerfile` (构建配置)

## 🎯 使用方法

### 全新安装

如果您是首次使用，只需要：

1. **下载启动脚本**
   ```bash
   # Linux/Mac
   curl -fsSL https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW/main/start.sh -o start.sh
   chmod +x start.sh
   ./start.sh
   
   # Windows (PowerShell)
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW/main/start.bat" -OutFile "start.bat"
   start.bat
   ```

2. **选择安装选项**
   - 选择菜单项 "6) 安装/更新环境"
   - 脚本会自动安装 Docker 和下载配置文件

3. **开始部署**
   - 安装完成后选择部署模式
   - 一键启动服务

### 现有环境更新

如果您已有环境，可以：

1. **更新配置文件**
   - 选择菜单项 "7) 下载配置文件"
   - 自动下载最新版本的配置

2. **更新环境**
   - 选择菜单项 "6) 安装/更新环境" 
   - 更新到最新版本的 Docker 和配置

## 📋 菜单说明

```
🚀 AI-CodeReview 部署模式选择
==================================================
1) 多容器模式 (推荐生产环境)
   - 基础版：仅启动 API + UI 服务
   - 完整版：启动 API + UI + Worker + Redis

2) 单容器模式 (适合开发测试)
   - 所有服务在一个容器中运行
   - 可选启用 Redis 支持

3) 停止所有服务

4) 查看服务状态

5) 查看服务日志

6) 安装/更新环境          ← 🆕 新增功能
   - 安装 Docker 和 Docker Compose
   - 下载最新配置文件

7) 下载配置文件           ← 🆕 新增功能
   - 下载/更新 docker-compose.yml
   - 下载/更新相关配置

0) 退出
==================================================
```

## 🔧 高级功能

### 离线部署
如果网络环境受限：

1. 手动下载必要文件
2. 将启动脚本的 `BASE_URL` 修改为本地路径
3. 跳过自动下载步骤

### 自定义配置
启动脚本支持：

- 自定义 Docker 镜像源
- 自定义配置文件来源
- 自定义安装路径

### 企业环境适配
- 支持代理配置
- 支持内网部署
- 支持离线镜像包

## 🚨 故障排除

### Docker 安装失败
```bash
# 手动安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### 配置文件下载失败
```bash
# 手动下载
wget https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW/main/docker-compose.yml
wget https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW/main/docker-compose.single.yml
```

### 权限问题
```bash
# Linux 添加用户到 docker 组
sudo usermod -aG docker $USER
newgrp docker
```

## 🎉 优势

### 简化部署流程
- 从零开始到服务运行，只需一个脚本
- 自动处理依赖安装和配置下载
- 智能错误检测和修复建议

### 统一跨平台体验
- Linux、Mac、Windows 统一操作方式
- 相同的菜单界面和功能
- 平台特定的优化处理

### 维护友好
- 自动更新到最新配置
- 版本兼容性检查
- 详细的日志和状态显示

现在您可以真正实现"一键部署"AI-CodeReview！
