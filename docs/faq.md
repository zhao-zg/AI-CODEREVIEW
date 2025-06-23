# �?AI-CodeReview-GitLab 常见问题解答 (FAQ)

## 📋 常见问题总览

本文档收集了用户在使�?AI-CodeReview-GitLab 过程中遇到的常见问题和解决方案�?

## 🚀 部署相关问题

### Q: Docker 容器启动失败怎么办？

**A:** 请按以下步骤排查�?

1. **检查日�?*
```bash
docker-compose logs app
```

2. **检查端口占�?*
```bash
# Windows
netstat -an | findstr :5001
netstat -an | findstr :5002

# Linux/macOS
netstat -tulpn | grep 5001
netstat -tulpn | grep 5002
```

3. **检查配置文�?*
```bash
# 确保配置文件存在
ls -la conf/.env

# 检查配置语�?
cat conf/.env | grep -v "^#" | grep -v "^$"
```

### Q: 为什么推荐使�?Docker Hub 镜像而不�?GHCR�?

**A:** 两个镜像仓库都可以使用，但有以下区别�?

| 特�?| Docker Hub | GitHub Container Registry |
|------|------------|---------------------------|
| 访问速度 | 国内访问较快 | 国内访问可能较慢 |
| 镜像大小 | 相同 | 相同 |
| 更新频率 | �?GitHub 同步 | �?GitHub 同步 |
| 免费额度 | 无限公开镜像 | 无限公开镜像 |

选择建议�?
- **国内用户**: 推荐 Docker Hub (`zzg1189/ai-codereview-gitlab`)
- **海外用户**: 两者都可以，GHCR 可能更快
- **企业用户**: 根据网络环境选择

### Q: 如何升级到最新版本？

**A:** 升级步骤�?

```bash
# 1. 停止当前服务
docker-compose down

# 2. 备份数据（可选但推荐�?
cp -r data data_backup_$(date +%Y%m%d)
cp -r conf conf_backup_$(date +%Y%m%d)

# 3. 拉取最新镜�?
docker-compose pull

# 4. 启动新版�?
docker-compose up -d

# 5. 验证服务状�?
docker-compose ps
curl http://localhost:5001/health
```

## ⚙️ 配置相关问题

### Q: 支持哪些 LLM 提供商？

**A:** 目前支持以下 LLM 提供商：

| 提供�?| 配置名称 | API Key 配置 | 备注 |
|--------|----------|-------------|------|
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` | 推荐，性价比高 |
| OpenAI | `openai` | `OPENAI_API_KEY` | 经典选择 |
| 智谱AI | `zhipuai` | `ZHIPUAI_API_KEY` | 国产�?|
| 通义千问 | `qwen` | `QWEN_API_KEY` | 阿里�?|
| Ollama | `ollama` | `OLLAMA_BASE_URL` | 本地部署 |

配置示例�?
```env
# 选择提供�?
LLM_PROVIDER=deepseek

# 配置对应�?API Key
DEEPSEEK_API_KEY=your_api_key_here
```

### Q: 如何配置 GitLab Webhook�?

**A:** GitLab Webhook 配置步骤�?

1. **在项目中创建配置文件**
```env
# conf/.env
GITLAB_URL=https://your-gitlab.com
GITLAB_TOKEN=your_access_token
GITLAB_WEBHOOK_SECRET=your_webhook_secret
```

2. **�?GitLab 项目中添�?Webhook**
   - 进入项目 Settings �?Webhooks
   - URL: `http://your-domain.com/api/webhook/gitlab`
   - Secret Token: 与配置文件中�?`GITLAB_WEBHOOK_SECRET` 一�?
   - Trigger: 选择 `Push events` �?`Merge request events`

3. **测试 Webhook**
```bash
curl -X POST http://your-domain.com/api/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: your_webhook_secret" \
  -d '{"test": true}'
```

### Q: 如何配置消息推送？

**A:** 支持多种消息推送方式：

**钉钉机器�?*
```env
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
```

**企业微信机器�?*
```env
WECOM_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

**飞书机器�?*
```env
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

## 🔧 功能使用问题

### Q: SVN 仓库如何配置�?

**A:** SVN 配置步骤�?

1. **挂载 SVN 仓库**
```yaml
# docker-compose.yml
volumes:
  - /path/to/your/svn/repo:/app/data/svn:ro
```

2. **配置 SVN 监控**
```env
# conf/.env
SVN_ENABLED=true
SVN_REPO_PATH=/app/data/svn
SVN_CHECK_INTERVAL=300  # 5分钟检查一�?
```

3. **设置 SVN 认证（如需要）**
```env
SVN_USERNAME=your_username
SVN_PASSWORD=your_password
```

### Q: 代码审查的质量如何控制？

**A:** 可以通过以下方式控制审查质量�?

1. **选择合适的 LLM 模型**
   - DeepSeek: 代码理解能力强，推荐
   - GPT-4: 质量最高，成本较高
   - 智谱AI: 中文支持�?

2. **调整审查参数**
```env
# 审查深度 (1-10)
REVIEW_DEPTH=7

# 是否包含建议
INCLUDE_SUGGESTIONS=true

# 审查语言
REVIEW_LANGUAGE=chinese
```

3. **配置审查模板**
编辑 `conf/prompt_templates.yml` 自定义审查提示词�?

### Q: 如何查看审查历史�?

**A:** 有多种方式查看审查历史：

1. **Web 界面**
   - 访问 `http://localhost:5002`
   - 查看 Dashboard 和详细记�?

2. **API 接口**
```bash
# 获取最近的审查记录
curl http://localhost:5001/api/reviews?limit=10

# 获取特定项目的审查记�?
curl http://localhost:5001/api/reviews?project=your-project
```

3. **数据库直接查�?*
```bash
# 进入容器
docker-compose exec app bash

# 查询数据�?
sqlite3 data/data.db "SELECT * FROM reviews ORDER BY created_at DESC LIMIT 10;"
```

## 🐛 故障排查

### Q: 服务响应很慢怎么办？

**A:** 排查步骤�?

1. **检查资源使�?*
```bash
# 查看容器资源使用
docker stats

# 查看系统资源
htop
```

2. **检�?LLM API 响应时间**
```bash
# 测试 API 响应
time curl -X POST http://localhost:5001/api/review \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"hello\")", "language": "python"}'
```

3. **优化配置**
```env
# 减少并发请求
MAX_CONCURRENT_REVIEWS=2

# 启用缓存
ENABLE_CACHE=true
CACHE_TTL=3600
```

### Q: 数据库损坏怎么修复�?

**A:** 数据库修复方法：

1. **备份当前数据�?*
```bash
cp data/data.db data/data.db.backup
```

2. **检查数据库完整�?*
```bash
sqlite3 data/data.db "PRAGMA integrity_check;"
```

3. **修复或重建数据库**
```bash
# 如果检查失败，重建数据�?
rm data/data.db
docker-compose restart app
```

### Q: Webhook 接收不到请求�?

**A:** 排查清单�?

1. **检查网络连通�?*
```bash
# �?GitLab/GitHub 服务器测�?
curl -I http://your-domain.com/api/webhook/gitlab
```

2. **检查防火墙设置**
```bash
# 确保端口开�?
ufw status
iptables -L
```

3. **检查日�?*
```bash
# 查看 webhook 相关日志
docker-compose logs app | grep webhook
```

4. **验证配置**
```bash
# 检�?webhook URL 和密�?
curl -X POST http://localhost:5001/api/webhook/test
```

## 📊 性能优化

### Q: 如何提高审查速度�?

**A:** 性能优化建议�?

1. **硬件优化**
   - 增加 CPU 核心�?
   - 增加内存容量
   - 使用 SSD 存储

2. **软件优化**
```env
# 启用缓存
ENABLE_CACHE=true

# 并发处理
MAX_WORKERS=4

# 批量处理
BATCH_SIZE=5
```

3. **LLM 优化**
   - 选择响应速度快的模型
   - 使用本地 Ollama 模型
   - 配置合适的超时时间

### Q: 如何减少存储空间占用�?

**A:** 存储优化方法�?

1. **启用自动清理**
```env
# 自动清理旧记录（天数�?
AUTO_CLEANUP_DAYS=30

# 压缩日志文件
LOG_ROTATION=true
```

2. **手动清理**
```bash
# 清理旧审查记�?
sqlite3 data/data.db "DELETE FROM reviews WHERE created_at < date('now', '-30 days');"

# 清理日志文件
find log/ -name "*.log*" -mtime +30 -delete
```

## 🔐 安全相关

### Q: 如何保护敏感信息�?

**A:** 安全建议�?

1. **使用环境变量**
```env
# 不要在代码中硬编码敏感信�?
API_KEY=${SECURE_API_KEY}
```

2. **设置适当的文件权�?*
```bash
chmod 600 conf/.env
chmod 700 data/
```

3. **使用 HTTPS**
```nginx
# Nginx 配置 SSL
ssl_certificate /path/to/certificate.crt;
ssl_certificate_key /path/to/private.key;
```

### Q: 如何限制访问权限�?

**A:** 权限控制方法�?

1. **网络层限�?*
```yaml
# docker-compose.yml
services:
  app:
    networks:
      - internal
networks:
  internal:
    internal: true
```

2. **应用层认�?*
```env
# 启用登录认证
ENABLE_AUTH=true
ADMIN_PASSWORD=your_secure_password
```

3. **反向代理限制**
```nginx
# Nginx IP 白名�?
allow 192.168.1.0/24;
deny all;
```

## 📞 获取帮助

如果以上 FAQ 没有解决您的问题，可以通过以下方式获取帮助�?

- **GitHub Issues**: https://github.com/zhao-zg/ai-codereview-gitlab/issues
- **部署指南**: [deployment_guide.md](deployment_guide.md)
- **项目文档**: https://github.com/zhao-zg/ai-codereview-gitlab/blob/main/README.md

---

*�?FAQ 会持续更新，欢迎提交您遇到的问题和解决方案�?
