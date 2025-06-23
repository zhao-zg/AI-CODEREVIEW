# 多SVN仓库监控配置指南

## 概述

本功能支持同时监控多个SVN仓库，每个仓库可以有独立的配置，包括远程URL、本地路径、认证信息和检查间隔等。

## 配置方法

### 基础配置

首先需要启用SVN检查功能：

```bash
# 启用SVN检查功能 (1=启用, 0=禁用)
SVN_CHECK_ENABLED=1

# 启用SVN代码审查功能 (1=启用, 0=禁用)
SVN_REVIEW_ENABLED=1

# SVN检查的定时任务表达式 (默认每30分钟检查一次)
SVN_CHECK_CRONTAB=*/30 * * * *
```

### 多仓库配置

在 `.env` 文件中配置 `SVN_REPOSITORIES` 环境变量，使用JSON格式：

```bash
SVN_REPOSITORIES=[
  {
    "name": "project_main",
    "remote_url": "svn://192.168.0.220/projectx/trunk",
    "local_path": "data/svn/project_main",
    "username": "your_username",
    "password": "your_password",
    "check_hours": 1
  },
  {
    "name": "project_dev",
    "remote_url": "svn://192.168.0.220/projectx/branches/dev",
    "local_path": "data/svn/project_dev",
    "username": "your_username",
    "password": "your_password", 
    "check_hours": 2
  }
]
```

### 单仓库配置（向后兼容）

如果只需要监控一个仓库，也可以使用传统的单仓库配置：

```bash
SVN_REMOTE_URL=svn://192.168.0.220/projectx/trunk
SVN_LOCAL_PATH=data/svn/project
SVN_USERNAME=your_username
SVN_PASSWORD=your_password
SVN_CHECK_INTERVAL_HOURS=1
SVN_CHECK_LIMIT=100
```

### 配置参数说明

#### 全局配置参数
- `SVN_CHECK_ENABLED`: 启用SVN检查功能 (1=启用, 0=禁用)
- `SVN_REVIEW_ENABLED`: 启用代码审查功能 (1=启用, 0=禁用)
- `SVN_CHECK_CRONTAB`: 定时检查的Cron表达式 (默认: `*/30 * * * *`)
- `SUPPORTED_EXTENSIONS`: 支持审查的文件扩展名 (逗号分隔，默认: `.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql`)

#### 多仓库配置参数 (SVN_REPOSITORIES JSON中的字段)
- `name`: 仓库名称，用于标识和日志显示 (必需)
- `remote_url`: SVN仓库的远程URL (必需)
- `local_path`: 本地检出路径 (必需)
- `username`: SVN用户名 (可选)
- `password`: SVN密码 (可选)
- `check_hours`: 检查最近多少小时的提交 (可选，默认24)

#### 单仓库配置参数 (向后兼容)
- `SVN_REMOTE_URL`: SVN远程仓库URL
- `SVN_LOCAL_PATH`: 本地检出路径
- `SVN_USERNAME`: SVN用户名
- `SVN_PASSWORD`: SVN密码
- `SVN_CHECK_INTERVAL_HOURS`: 检查间隔小时数 (默认1)
- `SVN_CHECK_LIMIT`: 每次检查的最大提交数量 (默认100)

## 使用方法

### 1. API接口

#### 检查所有仓库
```bash
curl -X POST http://localhost:5001/svn/check
```

#### 检查指定仓库
```bash
curl -X POST "http://localhost:5001/svn/check?repo=project_main"
```

#### 指定检查时间范围
```bash
curl -X POST "http://localhost:5001/svn/check?hours=6"
```

#### 组合参数
```bash
curl -X POST "http://localhost:5001/svn/check?repo=project_main&hours=12"
```

### 2. 命令行工具

#### 列出所有配置的仓库
```bash
python biz/cmd/svn_check.py --list-repos
```

#### 检查所有仓库
```bash
python biz/cmd/svn_check.py --hours 6
```

#### 检查指定仓库
```bash
python biz/cmd/svn_check.py --repo project_main --hours 12
```

#### 仅检查不审查
```bash
python biz/cmd/svn_check.py --repo project_dev --check-only
```

### 3. 定时任务

定时任务会自动检查所有配置的仓库。可以通过 `SVN_CHECK_CRONTAB` 环境变量配置检查频率：

```bash
# 每30分钟检查一次
SVN_CHECK_CRONTAB=*/30 * * * *

# 每小时检查一次
SVN_CHECK_CRONTAB=0 * * * *
```

## 向后兼容性

如果没有配置 `SVN_REPOSITORIES` 或者设置了 `SVN_REPOSITORIES=[]`，系统会自动回退到使用单仓库配置：

```bash
SVN_CHECK_ENABLED=1
SVN_REMOTE_URL=svn://192.168.0.220/projectx/trunk
SVN_LOCAL_PATH=data/svn/project
SVN_USERNAME=your_username
SVN_PASSWORD=your_password
SVN_CHECK_INTERVAL_HOURS=1
SVN_CHECK_LIMIT=100
SVN_REVIEW_ENABLED=1
SVN_CHECK_CRONTAB=*/30 * * * *
```

**注意**: 建议迁移到新的多仓库配置格式，单仓库配置在未来版本中可能会被废弃。

## 日志和通知

- 每个仓库的检查结果会在日志中分别显示
- 代码审查通知会包含仓库名称
- 错误信息会指明具体是哪个仓库出现问题

## 注意事项

1. 确保每个仓库的 `local_path` 都不相同，避免冲突
2. 建议为不同的仓库使用不同的检查间隔，避免同时进行大量操作
3. 仓库名称要唯一，用于标识和区分不同的仓库
4. JSON配置必须格式正确，建议使用JSON验证器检查格式

## 故障排除

### 配置解析错误
检查JSON格式是否正确，特别注意：
- 双引号而不是单引号
- 逗号分隔
- 括号匹配

### 仓库检出失败
- 检查远程URL是否正确
- 验证用户名密码
- 确保本地路径可写

### 仓库不存在错误
使用 `--list-repos` 命令查看实际配置的仓库名称。

## 完整配置示例

### 多仓库配置示例

```bash
# 启用SVN检查功能
SVN_CHECK_ENABLED=1

# 启用代码审查功能
SVN_REVIEW_ENABLED=1

# 每30分钟检查一次SVN变更
SVN_CHECK_CRONTAB=*/30 * * * *

# 支持的文件类型
SUPPORTED_EXTENSIONS=.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql

# 多仓库配置
SVN_REPOSITORIES=[
  {
    "name": "main_project",
    "remote_url": "svn://192.168.0.220/projectx/trunk",
    "local_path": "data/svn/main",
    "username": "developer",
    "password": "password123",
    "check_hours": 1
  },
  {
    "name": "dev_branch", 
    "remote_url": "svn://192.168.0.220/projectx/branches/development",
    "local_path": "data/svn/dev",
    "username": "developer",
    "password": "password123",
    "check_hours": 2
  },
  {
    "name": "release_branch",
    "remote_url": "svn://192.168.0.220/projectx/branches/release",
    "local_path": "data/svn/release", 
    "username": "developer",
    "password": "password123",
    "check_hours": 6
  }
]
```

### 单仓库配置示例（向后兼容）

```bash
# 启用SVN检查功能
SVN_CHECK_ENABLED=1

# 启用代码审查功能  
SVN_REVIEW_ENABLED=1

# SVN仓库配置
SVN_REMOTE_URL=svn://192.168.0.220/projectx/trunk
SVN_LOCAL_PATH=data/svn/project
SVN_USERNAME=developer
SVN_PASSWORD=password123

# 检查间隔和限制
SVN_CHECK_INTERVAL_HOURS=1
SVN_CHECK_LIMIT=100
SVN_CHECK_CRONTAB=*/30 * * * *

# 支持的文件类型
SUPPORTED_EXTENSIONS=.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql
```
