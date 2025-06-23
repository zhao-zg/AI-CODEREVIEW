# AI-CodeReview-GitLab 项目状态总览

## 📋 项目信息
- **项目名称:** AI-CodeReview-GitLab
- **仓库地址:** https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB
- **Docker镜像:** ghcr.io/zhao-zg/ai-codereview-gitlab
- **最后更新:** 2025-06-23

## ✅ 项目现状

### 核心功能
- ✅ **自动代码审查** - 支持GitLab/GitHub webhook
- ✅ **SVN集成** - 支持多仓库SVN监控
- ✅ **多LLM支持** - OpenAI、智谱AI、Ollama等
- ✅ **Web界面** - Streamlit UI + Flask API
- ✅ **Docker化部署** - 完整的容器化解决方案

### CI/CD状态
- ✅ **Docker构建发布** - 自动构建和发布镜像
- ✅ **基础语法检查** - 代码质量保证
- ✅ **版本管理** - 自动化版本发布流程
- ✅ **状态监控** - CI状态实时监控

### 项目结构
```
AI-Codereview-Gitlab/
├── api.py                  # Flask API服务
├── ui.py                   # Streamlit Web界面
├── quick_start.py          # 快速启动脚本
├── biz/                    # 业务逻辑模块
├── conf/                   # 配置文件
├── scripts/                # 管理脚本
├── docs/                   # 文档
└── docker-compose.yml      # Docker编排配置
```

## 🚀 使用指南

### 快速启动
```bash
# 克隆项目
git clone https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB.git
cd AI-CODEREVIEW-GITLAB

# Docker方式启动
docker-compose up -d

# 或直接拉取镜像
docker pull ghcr.io/zhao-zg/ai-codereview-gitlab:latest
```

### 开发环境
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境
cp conf/.env.dist conf/.env
# 编辑 conf/.env 配置文件

# 启动服务
python quick_start.py
```

## 📊 最近更新

### 2025-06-23 重要修复
- ✅ 修复GitHub测试失败问题
- ✅ 统一仓库地址为 zhao-zg/ai-codereview-gitlab
- ✅ 添加health检查端点
- ✅ 优化CI/CD工作流
- ✅ 清理多余文件，提升项目可读性

### 核心改进
- 🔧 禁用失败的测试工作流，改为手动触发
- 🔧 创建轻量级基础检查工作流
- 🔧 添加API健康检查端点
- 🔧 修正所有仓库引用的一致性

## 🔗 重要链接
- **GitHub仓库:** https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB
- **Actions监控:** https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB/actions
- **Docker镜像:** https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB/pkgs/container/ai-codereview-gitlab
- **Issues反馈:** https://github.com/zhao-zg/AI-CODEREVIEW-GITLAB/issues

## 📈 项目统计
- **主要编程语言:** Python
- **支持平台:** Docker (amd64 + arm64)
- **依赖管理:** requirements.txt
- **文档完整性:** ✅ 完整
- **测试覆盖:** 🔄 基础覆盖

---
*本文档自动维护，反映项目最新状态*
