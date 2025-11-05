# 定时任务并发控制机制说明

## 🔒 问题场景

**Q: 如果上次检查还在执行中（API还没返回），定时器又触发了新的检查，会怎么处理？**

---

## ✅ 解决方案：文件锁机制（已实现）

系统使用 **portalocker** 实现了**跨平台文件锁机制**，确保同一时刻只有一个检查任务在执行。

### 🎯 **核心原理**

```python
# api.py (第514-541行)

def acquire_svn_repo_lock(repo_name: str = "global"):
    """为特定仓库获取互斥锁"""
    import portalocker
    
    # 为每个仓库创建独立的锁文件
    safe_repo_name = "".join(c for c in repo_name if c.isalnum() or c in ('-', '_')).lower()
    lockfile_path = f"log/svn_check_{safe_repo_name}.lock"
    
    try:
        lockfile = open(lockfile_path, "w")
        # 尝试获取非阻塞互斥锁（LOCK_EX | LOCK_NB）
        portalocker.lock(lockfile, portalocker.LOCK_EX | portalocker.LOCK_NB)
        return lockfile  # 成功获取锁
    except portalocker.exceptions.LockException:
        lockfile.close()
        return None  # 锁已被占用，返回None

def release_svn_repo_lock(lockfile):
    """释放SVN仓库互斥锁"""
    portalocker.unlock(lockfile)
    lockfile.close()
```

---

## 📊 **完整流程图**

### **场景1：定时任务触发时上一次任务还在执行**

```
时间轴：
10:00:00  ┌─────────────────────────────────────┐
          │ 定时任务触发 #1                     │
          │ ├─ 尝试获取锁 (project1.lock)       │
          │ ├─ 成功！开始执行                   │
          │ ├─ SVN update...                    │
          │ ├─ 获取提交列表...                  │
          │ ├─ AI审查中... (需要5分钟)          │
          │                                     │
10:05:00  │ 🔄 定时任务触发 #2                  │
          │    ├─ 尝试获取锁 (project1.lock)    │
          │    ├─ ❌ 失败！锁已被任务#1占用     │
          │    ├─ 输出日志并跳过                │
          │    └─ 任务#2结束                    │
          │                                     │
10:06:00  │ ├─ 任务#1完成                       │
          │ ├─ 释放锁                           │
          └─────────────────────────────────────┘

10:10:00  ┌─────────────────────────────────────┐
          │ 🔄 定时任务触发 #3                  │
          │ ├─ 尝试获取锁 (project1.lock)       │
          │ ├─ ✅ 成功！锁已释放                │
          │ ├─ 开始执行...                      │
          └─────────────────────────────────────┘
```

---

## 🔧 **具体实现**

### **1️⃣ 全局SVN检查（使用全局锁）**

```python
# api.py (第588行)
def trigger_svn_check(hours: int = None):
    """触发SVN检查（全局模式使用全局锁）"""
    
    # 🔒 尝试获取全局锁
    lock = acquire_svn_repo_lock("global")
    if not lock:
        # ❌ 锁被占用，跳过本次检查
        logger.warning("已有全局SVN检查任务正在执行，跳过本次触发。")
        return
    
    try:
        # ✅ 成功获取锁，执行检查
        handle_multiple_svn_repositories(...)
    finally:
        # 🔓 无论成功失败，都释放锁
        release_svn_repo_lock(lock)
```

**日志示例**：
```
[2025-11-05 10:00:00] INFO: 开始检查 3 个SVN仓库
[2025-11-05 10:00:01] INFO: 开始检查仓库: project1
...
[2025-11-05 10:05:00] WARNING: 已有全局SVN检查任务正在执行，跳过本次触发。  ← 定时器触发但被跳过
...
[2025-11-05 10:06:00] INFO: SVN全局检查任务完成
[2025-11-05 10:10:00] INFO: 开始检查 3 个SVN仓库  ← 下次定时器成功执行
```

---

### **2️⃣ 单个仓库检查（使用仓库级锁）**

```python
# api.py (第623行)
def trigger_single_svn_repo_check(repo_config: dict):
    """触发单个SVN仓库检查（带仓库级互斥锁）"""
    
    repo_name = repo_config.get('name', 'unknown')
    
    # 🔒 为每个仓库获取独立的锁
    lock = acquire_svn_repo_lock(repo_name)
    if not lock:
        # ❌ 该仓库的锁被占用，跳过本次检查
        logger.warning(f"仓库 {repo_name} 已有检查任务正在执行，跳过本次检查。")
        return
    
    try:
        # ✅ 成功获取锁，执行检查
        handle_svn_changes(...)
    finally:
        # 🔓 释放锁
        release_svn_repo_lock(lock)
```

**优势**：
- ✅ **多仓库并行**：不同仓库的检查可以并行执行
- ✅ **仓库隔离**：project1正在检查时，project2仍然可以启动检查
- ✅ **避免重复**：同一个仓库不会同时有多个检查任务

---

### **3️⃣ 锁文件位置**

锁文件存储在 `log/` 目录下：

```bash
log/
├── svn_check_global.lock           # 全局锁
├── svn_check_project1.lock         # project1 仓库锁
├── svn_check_project2.lock         # project2 仓库锁
├── svn_check_high-freq-repo.lock   # high-freq-repo 仓库锁
└── ...
```

**锁文件特点**：
- 📁 **自动创建**：首次执行时自动创建
- 🔒 **互斥访问**：同一时刻只有一个进程可以持有锁
- 🌐 **跨平台**：Windows、Linux、macOS 都支持
- 🔄 **自动释放**：进程退出或异常时自动释放

---

## 📈 **性能表现**

### **场景测试：5分钟间隔，每次检查需要8分钟**

| 时间 | 定时器触发 | 实际执行 | 状态 |
|------|-----------|---------|------|
| 10:00 | ✅ 触发 #1 | ✅ 开始执行 | 获取锁成功 |
| 10:05 | ✅ 触发 #2 | ❌ 跳过 | 锁被占用 |
| 10:08 | - | ✅ 任务#1完成 | 释放锁 |
| 10:10 | ✅ 触发 #3 | ✅ 开始执行 | 获取锁成功 |
| 10:15 | ✅ 触发 #4 | ❌ 跳过 | 锁被占用 |
| 10:18 | - | ✅ 任务#3完成 | 释放锁 |
| 10:20 | ✅ 触发 #5 | ✅ 开始执行 | 获取锁成功 |

**结论**：
- ✅ 不会重复执行
- ✅ 不会积压任务
- ✅ 不会浪费资源
- ✅ 自动跳过冲突的触发

---

## 🎯 **多仓库并行示例**

假设有3个仓库，检查间隔都是5分钟：

```
10:00:00
├─ project1 触发 → ✅ 获取 project1.lock → 开始执行（需要8分钟）
├─ project2 触发 → ✅ 获取 project2.lock → 开始执行（需要3分钟）
└─ project3 触发 → ✅ 获取 project3.lock → 开始执行（需要5分钟）

10:03:00
└─ project2 完成 → 🔓 释放 project2.lock

10:05:00
├─ project1 触发 → ❌ project1.lock 被占用 → 跳过
├─ project2 触发 → ✅ 获取 project2.lock → 开始执行
└─ project3 触发 → ❌ project3.lock 被占用 → 跳过

10:05:00
└─ project3 完成 → 🔓 释放 project3.lock

10:08:00
└─ project1 完成 → 🔓 释放 project1.lock

10:10:00
├─ project1 触发 → ✅ 获取 project1.lock → 开始执行
├─ project2 触发 → ❌ project2.lock 被占用 → 跳过
└─ project3 触发 → ✅ 获取 project3.lock → 开始执行
```

**优势**：
- ✅ **不同仓库可以并行执行**
- ✅ **不会相互阻塞**
- ✅ **资源利用率高**

---

## ⚠️ **注意事项**

### **1. 锁超时问题**

如果进程异常退出（如被强制杀死），锁文件可能**不会自动释放**。

**解决方案**：
- ✅ 重启服务会自动清理（新的锁请求会检测到进程不存在）
- ✅ 手动删除锁文件：`rm log/svn_check_*.lock`

### **2. 过于频繁的定时任务**

如果定时间隔 < 实际执行时间，会出现大量"跳过"日志。

**示例**：
```bash
# 每30秒触发，但实际需要5分钟
SVN_CHECK_CRONTAB=*/30 * * * * *

# 结果：
10:00:00  ✅ 执行
10:00:30  ❌ 跳过
10:01:00  ❌ 跳过
10:01:30  ❌ 跳过
...
10:05:00  ✅ 执行完成
10:05:30  ✅ 执行
```

**建议**：
- ✅ 定时间隔 ≥ 实际执行时间
- ✅ 观察日志调整间隔

### **3. 多实例部署**

如果部署了多个API实例（如负载均衡），**锁文件必须在共享存储上**。

**方案**：
- 🔧 使用 **Redis 分布式锁**（推荐）
- 🔧 使用 **NFS/共享存储** 存放锁文件

---

## 📊 **监控和诊断**

### **查看锁文件状态**

```bash
# 查看所有锁文件
ls -lh log/svn_check_*.lock

# 查看锁文件内容（通常为空）
cat log/svn_check_project1.lock

# 检查是否有进程持有锁
lsof log/svn_check_project1.lock
```

### **查看日志**

```bash
# 查看跳过的触发
tail -f log/app.log | grep "跳过"

# 输出示例：
[2025-11-05 10:05:00] WARNING: 仓库 project1 已有检查任务正在执行，跳过本次检查。
[2025-11-05 10:10:00] WARNING: 已有全局SVN检查任务正在执行，跳过本次触发。
```

### **手动清理锁文件**

```bash
# 清理所有SVN锁文件（确保没有任务在执行）
rm -f log/svn_check_*.lock

# 清理特定仓库的锁
rm -f log/svn_check_project1.lock
```

---

## 🎯 **总结**

| 问题 | 解决方案 | 效果 |
|------|---------|------|
| **定时器冲突** | 文件锁机制 | ✅ 自动跳过 |
| **重复执行** | 非阻塞锁 | ✅ 避免重复 |
| **资源浪费** | 锁检测 | ✅ 不会积压 |
| **多仓库并发** | 仓库级锁 | ✅ 并行执行 |
| **跨平台兼容** | portalocker | ✅ 全平台支持 |

**系统设计非常健壮！** ✅

---

## 📚 **相关文档**

- 📖 [Cron表达式使用指南](./cron_expression_guide.md)
- 📖 [配置管理指南](./configuration_guide.md)
- 📖 [SVN配置指南](./svn_setup.md)
