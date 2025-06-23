#!/usr/bin/env python3
"""
环境配置初始化脚本
自动创建和配置.env文件
"""

import os
import shutil
from pathlib import Path

def check_env_file():
    """检查.env文件是否存在"""
    env_file = Path("conf/.env")
    env_dist_file = Path("conf/.env.dist")
    
    if env_file.exists():
        print("✅ .env文件已存在")
        return True
    
    if env_dist_file.exists():
        print("📋 发现.env.dist模板文件，正在创建.env文件...")
        shutil.copy(env_dist_file, env_file)
        print("✅ 已从模板创建.env文件")
        print("💡 请编辑 conf/.env 文件，配置你的API密钥和其他设置")
        return True
    
    print("❌ 未找到.env.dist模板文件")
    return False

def create_default_env():
    """创建默认的.env文件"""
    default_env_content = """#服务端口
SERVER_PORT=5001

#Timezone
TZ=Asia/Shanghai

#大模型供应商配置,支持 deepseek, openai,zhipuai,qwen 和 ollama
LLM_PROVIDER=deepseek

#DeepSeek settings (推荐 - 便宜好用)
DEEPSEEK_API_KEY=
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_MODEL=deepseek-chat

#OpenAI settings
OPENAI_API_KEY=
OPENAI_API_BASE_URL=https://api.openai.com/v1
OPENAI_API_MODEL=gpt-4o-mini

#ZhipuAI settings
ZHIPUAI_API_KEY=
ZHIPUAI_API_MODEL=GLM-4-Flash

#Qwen settings
QWEN_API_KEY=
QWEN_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_API_MODEL=qwen-coder-plus

#OllaMA settings; 注意: 如果使用 Docker 部署，127.0.0.1 指向的是容器内部的地址。请将其替换为实际的 Ollama服务器IP地址。
OLLAMA_API_BASE_URL=http://127.0.0.1:11434
OLLAMA_API_MODEL=llama3.1

#审查风格: professional, sarcastic, gentle, humorous
REVIEW_STYLE=professional

#企业微信消息推送: 0不发送企业微信消息,1发送企业微信消息
WX_WORK_ENABLED=0
WX_WORK_WEBHOOK_URL=

#钉钉消息推送: 0不发送钉钉消息,1发送钉钉消息
DINGTALK_ENABLED=0
DINGTALK_WEBHOOK_URL=

#GitLab配置
GITLAB_ACCESS_TOKEN=
GITLAB_BASE_URL=https://gitlab.com

#GitHub配置
GITHUB_ACCESS_TOKEN=

#SVN配置
SVN_REPOSITORY_URL=
SVN_USERNAME=
SVN_PASSWORD=
SVN_CHECK_INTERVAL=300

#数据库配置
DATABASE_URL=sqlite:///data/data.db

#Dashboard配置
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=admin123
DASHBOARD_SECRET_KEY=your-secret-key-here

#版本追踪配置
VERSION_TRACKING_ENABLED=1
REUSE_PREVIOUS_REVIEW_RESULT=1
VERSION_TRACKING_RETENTION_DAYS=30

#日志配置
LOG_LEVEL=INFO
"""
    
    env_file = Path("conf/.env")
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(default_env_content)
    
    print("✅ 已创建默认.env文件")
    return True

def create_directories():
    """创建必要的目录"""
    directories = [
        "conf",
        "data",
        "log",
        "data/svn",
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ 目录已创建: {dir_path}")

def show_configuration_guide():
    """显示配置指南"""
    print("\n" + "="*60)
    print("🚀 环境配置初始化完成！")
    print("="*60)
    print("\n📝 下一步配置指南:")
    print("\n1. 编辑配置文件:")
    print("   vi conf/.env  # Linux/Mac")
    print("   notepad conf\\.env  # Windows")
    
    print("\n2. 必需配置项:")
    print("   ✅ LLM_PROVIDER - 选择AI服务商 (deepseek推荐)")
    print("   ✅ *_API_KEY - 对应AI服务商的API密钥")
    print("   ✅ GITLAB_ACCESS_TOKEN - GitLab访问令牌(如果使用GitLab)")
    print("   ✅ GITHUB_ACCESS_TOKEN - GitHub访问令牌(如果使用GitHub)")
    
    print("\n3. 可选配置项:")
    print("   🔧 WX_WORK_* - 企业微信通知")
    print("   🔧 DINGTALK_* - 钉钉通知")
    print("   🔧 SVN_* - SVN代码审查")
    print("   🔧 DASHBOARD_* - 仪表板登录")
    
    print("\n4. 启动服务:")
    print("   docker-compose up -d")
    
    print("\n5. 访问服务:")
    print("   🌐 API服务: http://localhost:5001")
    print("   📊 仪表板: http://localhost:5002")
    
    print("\n📖 详细文档:")
    print("   - 部署指南: doc/deployment_guide.md")
    print("   - FAQ: doc/faq.md")
    print("   - 自动构建: DOCKER_AUTO_BUILD.md")

def main():
    """主函数"""
    print("🔧 初始化环境配置...")
    
    # 创建必要目录
    create_directories()
    
    # 检查或创建.env文件
    if not check_env_file():
        print("📝 创建默认配置文件...")
        create_default_env()
    
    # 显示配置指南
    show_configuration_guide()

if __name__ == "__main__":
    main()
