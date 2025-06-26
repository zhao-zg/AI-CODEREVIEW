# ⚙️ 配置管理功能使用指南

## 📋 功能概述

AI-CodeReview-GitLab 现在提供了完整的Web界面配置管理功能，让您可以通过浏览器轻松管理所有系统配置，无需手动编辑配置文件。

## 🚀 快速开始

### 1. 访问配置管理界面

1. 启动系统：
   ```bash
   # 方式1：一键启动
   python quick_start.py
   
   # 方式2：手动启动
   streamlit run ui.py --server.port=8501 --server.address=0.0.0.0
   ```

2. 打开浏览器访问：`http://localhost:8501`

3. 使用管理员账号登录（默认用户名/密码：admin/admin）

4. 在侧边栏选择"⚙️ 配置管理"

### 2. 配置管理界面

配置管理分为三个主要模块：

#### 🤖 环境配置
- **AI模型配置**：选择和配置不同的AI模型提供商
- **GitLab/GitHub配置**：设置版本控制系统集成
- **SVN配置**：配置SVN仓库和认证信息
- **消息推送配置**：配置钉钉、飞书、企业微信推送
- **数据库配置**：设置数据存储选项
- **系统配置**：日志级别、端口等系统参数

#### 🎨 界面配置
- **基础设置**：仪表板标题、图标、布局
- **图表设置**：图表高度、配色方案
- **性能设置**：缓存、自动刷新间隔

#### 📝 提示模板
- **系统提示词**：设置AI模型的系统角色
- **用户提示词**：定义代码审查的具体要求
- **模板管理**：添加、编辑、删除提示模板

## 🔧 详细配置说明

### AI模型配置

#### OpenAI配置
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
```

#### DeepSeek配置
```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
```

#### Ollama配置
```
LLM_PROVIDER=ollama
OLLAMA_API_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama
```

#### Jedi配置
```
LLM_PROVIDER=jedi
JEDI_API_KEY=your-jedi-token
JEDI_API_BASE_URL=https://jedi-jp-prd-ai-tools.bekko.com:30001/chat_completion_api
JEDI_API_MODEL=official-deepseek-r1
```

### 版本控制配置

#### GitLab配置
```
GITLAB_ACCESS_TOKEN=glpat-your-token
GITLAB_URL=https://gitlab.example.com
GITLAB_WEBHOOK_SECRET=your-webhook-secret
```

#### GitHub配置
```
GITHUB_ACCESS_TOKEN=ghp_your-token
GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

#### SVN配置
```json
SVN_REPOSITORIES={
  "project1": {
    "url": "svn://server/project1",
    "username": "user",
    "password": "pass"
  }
}
```

### 消息推送配置

#### 钉钉配置
```
DINGTALK_ENABLED=1
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=your-token
```

#### 飞书配置
```
FEISHU_ENABLED=1
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-token
```

#### 企业微信配置
```
WECOM_ENABLED=1
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key
```

## 💡 使用技巧

### 1. 配置验证
- 在保存配置前，使用"🧪 测试配置"功能验证配置的正确性
- 系统会检查必要的参数是否填写、格式是否正确

### 2. 配置备份
- 修改配置前建议先使用"📥 导出配置"功能备份当前配置
- 系统会自动创建配置文件的备份副本

### 3. 配置管理最佳实践
- **环境变量配置**：修改后需要重启服务才能生效
- **界面配置**：保存后刷新页面即可看到效果
- **提示模板**：新模板在下次代码审查时生效

### 4. 敏感信息安全
- API密钥等敏感信息在界面中以密码形式显示
- 配置文件存储在本地，请确保服务器安全
- 定期更换API密钥和访问令牌

## 🛠️ 高级功能

### 1. 自定义提示模板

您可以创建专门的提示模板来满足特定需求：

```yaml
# 安全审查模板
security_review_prompt:
  system: "你是一个专业的代码安全审查专家，专注于发现潜在的安全漏洞。"
  user: "请审查以下代码的安全性，重点关注：1. SQL注入 2. XSS攻击 3. 权限控制 4. 数据泄露\n\n代码：{code_diff}"

# 性能优化模板  
performance_review_prompt:
  system: "你是一个代码性能优化专家，专注于提升代码效率。"
  user: "请审查以下代码的性能，提供优化建议：{code_diff}"
```

### 2. 多项目配置

对于多个项目，可以配置不同的消息推送：

```
# 项目A的钉钉群
DINGTALK_WEBHOOK_URL_PROJECT_A=https://oapi.dingtalk.com/robot/send?access_token=token-a

# 项目B的钉钉群
DINGTALK_WEBHOOK_URL_PROJECT_B=https://oapi.dingtalk.com/robot/send?access_token=token-b
```

### 3. 界面个性化

自定义仪表板外观：

- **配色方案**：选择符合公司品牌的颜色
- **标题和图标**：设置个性化的标题和emoji图标
- **布局**：选择宽屏或居中布局
- **性能设置**：根据数据量调整缓存和刷新间隔

## 🔍 故障排除

### 常见问题

1. **配置保存失败**
   - 检查文件权限：确保应用有写入`conf/`目录的权限
   - 检查磁盘空间：确保有足够的磁盘空间
   - 查看错误日志：检查控制台输出的错误信息

2. **配置不生效**
   - 环境变量配置需要重启服务
   - 界面配置需要刷新页面
   - 提示模板需要触发新的代码审查

3. **API连接失败**
   - 检查API密钥是否正确
   - 检查网络连接和防火墙设置
   - 验证API服务是否可访问

### 调试技巧

1. **查看日志**：
   ```bash
   tail -f log/app.log
   ```

2. **测试API连接**：
   ```bash
   curl -H "Authorization: Bearer your-api-key" https://api.example.com/v1/test
   ```

3. **验证配置文件**：
   ```bash
   cat conf/.env | grep -v "^#" | grep -v "^$"
   ```

## 📚 相关文档

- [部署指南](deployment_guide.md)
- [使用手册](ui_guide.md)
- [常见问题](faq.md)
- [API文档](../README.md)

## 🆘 获取帮助

如果您在使用配置管理功能时遇到问题：

1. 查看本指南的故障排除部分
2. 检查项目的[常见问题文档](faq.md)
3. 在GitHub上提交[Issue](https://github.com/zzg1189/ai-codereview-gitlab/issues)
4. 加入技术交流群获取支持

---

**🎉 享受全新的配置管理体验！** 通过Web界面管理配置，让AI代码审查系统的使用更加便捷高效。
