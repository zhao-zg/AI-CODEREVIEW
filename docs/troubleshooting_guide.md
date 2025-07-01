# 🛠️ 兼容性和故障排除指南

## 📋 Streamlit版本兼容性

### 支持的版本
- **推荐版本**: Streamlit 1.27.0+
- **最低版本**: Streamlit 1.18.0
- **当前测试版本**: Streamlit 1.23.1

### 版本差异说明

#### Streamlit 1.27.0+
- ✅ 支持 `st.rerun()` 方法
- ✅ 最新的UI组件和功能
- ✅ 最佳性能和稳定性

#### Streamlit 1.18.0 - 1.26.x
- ⚠️ 使用 `st.experimental_rerun()` 方法
- ⚠️ 部分新功能可能不支持
- ✅ 基本功能正常

#### Streamlit < 1.18.0
- ❌ 不推荐使用
- ❌ 可能存在兼容性问题
- ❌ 缺少重要功能

## 🔧 常见问题及解决方案

### 1. AttributeError: module 'streamlit' has no attribute 'rerun'

**问题描述**: 
```
AttributeError: module 'streamlit' has no attribute 'rerun'
```

**解决方案**:

#### 方案一: 升级Streamlit (推荐)
```bash
pip install streamlit --upgrade
```

#### 方案二: 使用兼容性修复脚本
```bash
python scripts/streamlit_compatibility_check.py
```

#### 方案三: 手动修复
系统已内置兼容性处理，如果仍有问题，请检查是否正确导入了兼容函数。

### 2. 页面无法正常刷新

**问题描述**: 
点击按钮后页面不刷新，或显示"请手动刷新页面"提示。

**解决方案**:
1. 检查Streamlit版本：`streamlit --version`
2. 升级到最新版本：`pip install streamlit --upgrade`
3. 手动刷新浏览器页面

### 3. 配置保存后不生效

**问题描述**: 
在配置管理界面修改配置后，更改没有生效。

**解决方案**:
1. **环境配置**: 需要重启整个服务
   ```bash
   # 停止服务
   Ctrl+C
   
   # 重新启动
   python ui.py
   ```

2. **界面配置**: 只需刷新页面
   ```bash
   # 在浏览器中按 F5 或 Ctrl+R
   ```

3. **提示模板**: 在下次代码审查时生效

### 4. 导入错误

**问题描述**: 
```
ImportError: cannot import name 'ConfigManager' from 'biz.utils.config_manager'
```

**解决方案**:
1. 检查文件路径是否正确
2. 确保所有必要的文件都存在
3. 重新运行初始化脚本：
   ```bash
   python scripts/init_env.py
   ```

### 5. 编码错误

**问题描述**: 
```
UnicodeDecodeError: 'utf-8' codec can't decode bytes
```

**解决方案**:
1. 检查配置文件编码：
   ```bash
   # Windows
   Get-Content conf\.env -Encoding UTF8 | Out-File conf\.env.new -Encoding UTF8
   Move-Item conf\.env.new conf\.env
   ```

2. 重新生成配置文件：
   ```bash
   python scripts/init_env.py
   ```

## 🧪 测试和验证

### 1. 环境检查
```bash
# 检查Python版本
python --version

# 检查Streamlit版本  
streamlit --version

# 检查依赖包
pip list | findstr streamlit
```

### 2. 模块测试
```bash
# 测试配置管理模块
python -c "from biz.utils.config_manager import ConfigManager; print('✅ ConfigManager OK')"

# 测试UI模块语法
python -c "import ast; ast.parse(open('ui.py').read()); print('✅ UI syntax OK')"
```

### 3. 功能测试
```bash
# 运行兼容性检查
python scripts/streamlit_compatibility_check.py

# 运行项目验证
python scripts/final_project_validation.py
```

## 🔄 升级指南

### 从旧版本升级

1. **备份配置**:
   ```bash
   cp conf/.env conf/.env.backup
   cp conf/dashboard_config.py conf/dashboard_config.py.backup
   ```

2. **更新代码**:
   ```bash
   git pull origin main
   ```

3. **升级依赖**:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **迁移配置**:
   ```bash
   python scripts/init_env.py
   ```

5. **验证功能**:
   ```bash
   python scripts/final_project_validation.py
   ```

### Streamlit升级
```bash
# 查看当前版本
streamlit --version

# 升级到最新版本
pip install streamlit --upgrade

# 验证升级
streamlit --version

# 测试功能
python ui.py
```

## 📱 浏览器兼容性

### 支持的浏览器
- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+

### 推荐设置
- **分辨率**: 1280x720+
- **JavaScript**: 必须启用
- **Cookie**: 必须启用
- **本地存储**: 必须启用

## 🐳 Docker环境问题

### 容器启动失败
```bash
# 检查容器状态
docker ps -a

# 查看容器日志
docker logs <container_name>

# 重新构建镜像
docker-compose up --build
```

### 端口冲突
```bash
# 检查端口占用
netstat -an | findstr :5002

# 修改配置文件 conf/.env 中的 UI_PORT
UI_PORT=8502

# 重新启动
python ui.py
```

## 📞 获取帮助

### 1. 自助解决
- 查看本故障排除指南
- 运行兼容性检查脚本
- 查看项目日志文件

### 2. 社区支持
- GitHub Issues: [提交问题](https://github.com/zhao-zg/ai-codereview/issues)
- 项目文档: [查看文档](../docs/)
- 常见问题: [FAQ](docs/faq.md)

### 3. 错误报告
提交问题时请包含以下信息：
- 操作系统和版本
- Python版本
- Streamlit版本
- 完整的错误信息
- 复现步骤

## 🎯 最佳实践

### 1. 环境管理
- 使用虚拟环境隔离依赖
- 定期更新依赖包
- 备份重要配置文件

### 2. 性能优化
- 启用Streamlit缓存功能
- 合理设置自动刷新间隔
- 监控系统资源使用

### 3. 安全建议
- 定期更换API密钥
- 使用强密码保护管理界面
- 限制网络访问权限

---

**💡 提示**: 如果遇到本指南未覆盖的问题，请查看项目的其他文档或提交Issue寻求帮助。
