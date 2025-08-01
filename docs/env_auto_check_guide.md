# 环境配置自动检查功能

## 功能概述

AI-CodeReview 系统现在具备智能的环境配置检查功能，可以在启动时自动：

1. **检测 `.env` 文件是否存在**
   - 如果不存在，自动从 `.env.dist` 复制创建
   - 确保项目首次运行时配置文件完整

2. **检查配置参数完整性**
   - 对比 `.env.dist` 和 `.env` 中的参数
   - 自动补充缺失的配置项和默认值
   - 保持配置文件与模板同步

3. **验证关键配置项**
   - 检查核心参数是否设置
   - 提供配置摘要和建议
   - 确保服务正常启动

## 使用方法

### 自动检查（推荐）

环境配置检查已集成到启动脚本中，无需额外操作：

**Windows 用户：**
```cmd
start_windows.bat
```

**Linux/Mac 用户：**
```bash
./start.sh
```

启动时会自动执行环境检查，输出类似：
```
[1/4] 检查环境配置...
[INFO] 开始环境配置检查...
[INFO] 环境配置完整，所有必需参数都已存在
[INFO] ✅ 环境配置检查完成，可以启动服务
```

### 手动检查

如需单独运行环境配置检查：

**Python 版本（推荐）：**
```bash
python scripts/env_checker.py
```

**Windows 批处理版本：**
```cmd
scripts\env_checker.bat
```

## 检查流程

### 1. 文件存在性检查

```
conf_templates/.env.dist (模板文件) ──┐
                         ├─ 比较 ── 检测差异
conf/.env (配置文件) ────┘
```

### 2. 处理逻辑

| 情况 | 处理方式 |
|------|----------|
| `.env` 不存在 | 完整复制 `.env.dist` → `.env` |
| `.env` 存在但不完整 | 追加缺失参数到 `.env` |
| `.env` 完整 | 无需修改，显示摘要 |
| `.env.dist` 不存在 | 报错退出 |

### 3. 输出示例

**首次运行（.env 不存在）：**
```
[WARNING] 环境配置文件 conf/.env 不存在
[INFO] 正在从 conf_templates/.env.dist 复制配置...
[INFO] ✅ 成功创建 conf/.env
```

**补充缺失参数：**
```
[WARNING] 发现 6 个缺失的环境变量:
[WARNING]   - GITHUB_URL
[WARNING]   - WORKER_QUEUE
[WARNING]   - SVN_REMOTE_URL
[INFO] 正在补充缺失的环境变量...
[INFO] ✅ 环境配置更新完成
```

**配置完整：**
```
[INFO] ✅ 环境配置完整，所有必需参数都已存在
```

## 配置摘要

检查完成后会显示配置摘要：

```
==================================================
主要配置项:
  LLM_PROVIDER: jedi
  TZ: Asia/Shanghai
  VERSION_TRACKING_ENABLED: 1
  LOG_LEVEL: DEBUG

已配置的AI模型: deepseek, openai, zhipuai, qwen, jedi
总配置项数量: 61
==================================================
```

## 关键配置项验证

系统会特别检查以下关键配置：

- `LLM_PROVIDER`: AI模型供应商
- `TZ`: 时区设置

如果缺失，会显示警告提示。

## 技术实现

### 脚本文件

1. **`scripts/env_checker.py`** - Python实现（主要版本）
   - 功能完整，支持详细日志
   - 跨平台兼容
   - 智能参数解析

2. **`scripts/env_checker.bat`** - Windows批处理实现
   - 简化版本，作为备选
   - 纯Windows命令，无依赖

### 集成方式

- **Linux/Mac**: `start.sh` 中的 `check_environment_config()` 函数
- **Windows**: `start_windows.bat` 优先使用Python版本，降级到批处理版本

### 错误处理

- 文件权限问题：提示并继续
- Python不可用：降级到批处理版本（Windows）
- 配置文件损坏：详细错误信息
- 网络问题：跳过非关键检查

## 常见问题

### Q: 检查器修改了我的.env文件怎么办？
A: 检查器只会**追加**缺失的参数，不会修改现有配置。所有追加的内容都有明确标注。

### Q: 如何跳过环境检查？
A: 环境检查失败不会阻止启动，只会显示警告。如需完全跳过，可以直接运行Docker命令。

### Q: 添加了新的配置项怎么办？
A: 更新 `.env.dist` 文件后，下次启动时检查器会自动检测并补充新参数到 `.env`。

### Q: 检查器报错怎么办？
A: 
1. 确保 `conf_templates/.env.dist` 文件存在且格式正确
2. 检查文件权限
3. 查看详细错误信息并修复

## 维护建议

1. **保持模板更新**: 新增配置时同步更新 `.env.dist`
2. **格式规范**: 遵循 `KEY=VALUE` 格式，避免特殊字符
3. **文档同步**: 重要配置变更时更新相关文档
4. **测试验证**: 可运行 `python test_env_checker.py` 进行功能测试

## 相关文件

```
AI-Codereview/
├── conf/
│   ├── .env.dist          # 配置模板（版本控制）
│   └── .env               # 实际配置（自动生成/更新）
├── scripts/
│   ├── env_checker.py     # Python环境检查器
│   └── env_checker.bat    # Windows批处理检查器
├── start.sh               # Linux/Mac启动脚本
├── start_windows.bat      # Windows启动脚本
└── test_env_checker.py    # 功能测试脚本
```

这个环境配置检查功能让部署更加自动化和用户友好，减少了手动配置的工作量和出错可能性。
