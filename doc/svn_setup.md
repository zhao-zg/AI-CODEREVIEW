# SVN代码审查配置指南

本文档展示如何配置SVN代码审查功能，支持单仓库和多仓库两种配置模式。

## 前提条件

1. 已安装SVN客户端（如TortoiseSVN）
2. 有访问SVN仓库的权限
3. 已配置好基本的代码审查环境

## 配置步骤

### 1. 选择配置模式

#### 模式A: 单仓库配置（简单模式）

适用于只需要监控一个SVN仓库的场景。

在 `conf/.env` 文件中添加以下配置：

```bash
# 启用SVN检查功能
SVN_CHECK_ENABLED=1

# SVN仓库配置
SVN_REMOTE_URL=svn://your-svn-server/your-project/trunk
SVN_LOCAL_PATH=data/svn/your-project
SVN_USERNAME=your_username
SVN_PASSWORD=your_password

# 检查设置
SVN_CHECK_INTERVAL_HOURS=1
SVN_CHECK_LIMIT=100
SVN_CHECK_CRONTAB=*/30 * * * *

# 启用代码审查
SVN_REVIEW_ENABLED=1

# 支持的文件类型
SUPPORTED_EXTENSIONS=.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql
```

#### 模式B: 多仓库配置（推荐）

适用于需要同时监控多个SVN仓库的场景，配置更灵活。

在 `conf/.env` 文件中添加以下配置：

```bash
# 启用SVN检查功能
SVN_CHECK_ENABLED=1

# 多仓库配置（JSON格式）
SVN_REPOSITORIES=[
  {
    "name": "main_project",
    "remote_url": "svn://your-svn-server/your-project/trunk",
    "local_path": "data/svn/main",
    "username": "your_username",
    "password": "your_password",
    "check_hours": 1
  }
]

# 全局设置
SVN_CHECK_CRONTAB=*/30 * * * *
SVN_REVIEW_ENABLED=1
SUPPORTED_EXTENSIONS=.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql
```

### 2. 测试配置

#### 测试单仓库配置

```bash
# 仅检查变更，不进行审查
python biz/cmd/svn_check.py --svn-url svn://your-server/project --svn-path data/svn/project --check-only

# 检查并审查最近8小时的提交
python biz/cmd/svn_check.py --svn-url svn://your-server/project --svn-path data/svn/project --hours 8
```

#### 测试多仓库配置

```bash
# 列出所有配置的仓库
python biz/cmd/svn_check.py --list-repos

# 检查所有仓库
python biz/cmd/svn_check.py --hours 8

# 检查指定仓库
python biz/cmd/svn_check.py --repo main_project --hours 8
```

### 3. 启动服务

```bash
python api.py
```

## 工作流程

1. **定时检查**: 系统按照配置的时间间隔（默认30分钟）检查SVN
2. **更新工作副本**: 执行 `svn update` 获取最新代码
3. **获取提交记录**: 查询指定时间范围内的提交
4. **分析变更**: 对每个提交的文件变更进行分析
5. **代码审查**: 使用AI模型审查代码变更
6. **发送通知**: 将审查结果发送到配置的通知渠道

## 注意事项

### Windows路径问题
- 使用正斜杠 `/` 或双反斜杠 `\\` 来表示路径
- 示例：`C:/code/project` 或 `C:\\code\\project`

### SVN凭据管理
- 建议使用SVN的凭据缓存功能
- 或者在SVN客户端中保存登录信息

### 权限问题
- 确保运行程序的用户有访问SVN工作副本的权限
- 确保能够执行 `svn` 命令

## 故障排除

### 常见错误

1. **SVN路径不存在**
   ```
   错误: SVN路径不存在: C:\code\your-project
   ```
   解决：检查路径是否正确，确保目录存在

2. **不是SVN工作目录**
   ```
   错误: 指定路径不是SVN工作目录
   ```
   解决：确保目录包含 `.svn` 文件夹

3. **SVN命令执行失败**
   ```
   执行SVN命令失败: svn: E155007: ...
   ```
   解决：检查SVN客户端是否正确安装，工作副本是否损坏

### 调试方法

1. **查看日志**
   ```bash
   tail -f log/app.log
   ```

2. **测试SVN命令**
   ```bash
   cd C:\code\your-project
   svn status
   svn log -l 5
   ```

3. **检查环境变量**
   ```python
   import os
   print(os.environ.get('SVN_PATH'))
   ```

## 示例场景

### 场景1：开发团队日常使用

```bash
# 配置每15分钟检查一次，审查最近2小时的提交
SVN_CHECK_CRONTAB=*/15 * * * *
SVN_CHECK_HOURS=2
```

### 场景2：夜间批量检查

```bash
# 每天凌晨2点检查前一天的所有提交
SVN_CHECK_CRONTAB=0 2 * * *
SVN_CHECK_HOURS=24
```

### 场景3：仅工作时间检查

```bash
# 工作日的工作时间每30分钟检查一次
SVN_CHECK_CRONTAB=*/30 9-18 * * 1-5
```

## API接口

### 手动触发检查

```bash
curl -X POST http://localhost:5001/svn/check
```

响应示例：
```json
{
  "message": "SVN检查已启动，将异步处理"
}
```
