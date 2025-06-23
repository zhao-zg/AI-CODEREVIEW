#!/usr/bin/env python3
"""
快速启动脚本
检查并创建.env文件，然后启动服务
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def create_env_if_not_exists():
    """如果.env文件不存在，则创建它"""
    env_file = Path("conf/.env")
    env_dist_file = Path("conf/.env.dist")
    
    if env_file.exists():
        print("✅ .env 文件已存在")
        return True
    
    # 确保conf目录存在
    Path("conf").mkdir(exist_ok=True)
    
    if env_dist_file.exists():
        print("📋 从模板创建 .env 文件...")
        shutil.copy(env_dist_file, env_file)
        print("✅ 已从 .env.dist 创建 .env 文件")
    else:
        print("📝 创建默认 .env 文件...")
        create_default_env_file(env_file)
        print("✅ 已创建默认 .env 文件")
    
    return True

def create_default_env_file(env_file_path):
    """创建默认的.env文件"""
    default_content = """# AI代码审查系统配置文件

#服务端口
SERVER_PORT=5001

#时区
TZ=Asia/Shanghai

#大模型供应商配置,支持 deepseek, openai, zhipuai, qwen 和 ollama
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

#审查风格: professional, sarcastic, gentle, humorous
REVIEW_STYLE=professional

#企业微信消息推送: 0不发送,1发送
WX_WORK_ENABLED=0
WX_WORK_WEBHOOK_URL=

#钉钉消息推送: 0不发送,1发送
DINGTALK_ENABLED=0
DINGTALK_WEBHOOK_URL=

#GitLab配置
GITLAB_ACCESS_TOKEN=
GITLAB_BASE_URL=https://gitlab.com

#GitHub配置
GITHUB_ACCESS_TOKEN=

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
    
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.write(default_content)

def check_api_key_configured():
    """检查API密钥是否已配置"""
    env_file = Path("conf/.env")
    if not env_file.exists():
        return False
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有配置的API密钥
        if "DEEPSEEK_API_KEY=" in content:
            lines = content.split('\n')
            for line in lines:
                if line.startswith('DEEPSEEK_API_KEY=') and not line.endswith('='):
                    return True
        
        return False
    except:
        return False

def create_directories():
    """创建必要的目录"""
    dirs = ["data", "log", "data/svn", "conf"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("✅ 必要目录已创建")

def main():
    """主函数"""
    print("🚀 AI代码审查系统快速启动")
    print("=" * 40)
    
    # 创建目录
    create_directories()
    
    # 创建.env文件
    create_env_if_not_exists()
    
    # 检查API密钥配置
    if not check_api_key_configured():
        print("\n" + "⚠️" * 3 + " 重要提醒 " + "⚠️" * 3)
        print("检测到API密钥未配置！")
        print("\n📝 请按以下步骤配置：")
        print("1. 编辑文件: conf/.env")
        print("2. 设置API密钥，例如:")
        print("   DEEPSEEK_API_KEY=your_api_key_here")
        print("\n💡 推荐使用DeepSeek（便宜好用）")
        print("   获取API密钥: https://platform.deepseek.com/")
        
        response = input("\n是否继续启动服务？(y/N): ").lower()
        if response != 'y':
            print("✋ 已取消启动，请配置API密钥后重新运行")
            return 1
    
    print("\n🚀 启动服务...")
    print("💡 提示: 如果是首次运行，Docker需要下载镜像，请耐心等待")
    
    # 启动docker-compose
    try:
        result = subprocess.run(["docker-compose", "up", "-d"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\n✅ 服务启动成功！")
            print("\n🌐 访问地址:")
            print("   - API服务: http://localhost:5001")
            print("   - 仪表板: http://localhost:5002")
            print("\n📊 查看状态: docker-compose ps")
            print("📝 查看日志: docker-compose logs -f")
            print("🛑 停止服务: docker-compose down")
        else:
            print(f"\n❌ 启动失败:")
            print(result.stderr)
            return 1
            
    except FileNotFoundError:
        print("\n❌ 未找到docker-compose命令")
        print("请确保已安装Docker和Docker Compose")
        return 1
    except Exception as e:
        print(f"\n❌ 启动时发生错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
