#!/usr/bin/env python3
"""
环境配置初始化脚本 - 增强版
自动创建和配置完整的 .env 文件，确保所有必需的配置项都存在
解决 docker-compose 部署时 .env 数据不完整的问题
"""

import os
import shutil
from pathlib import Path

def escape_env_value(value: str) -> str:
    """
    安全地转义环境变量值
    处理包含特殊字符的值，如双引号、换行符等
    """
    if not value:
        return ""
    
    # 如果值已经被引号包围，先去掉外层引号
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    
    # 检查是否需要加引号的条件
    needs_quotes = any([
        ' ' in value,      # 包含空格
        '"' in value,      # 包含双引号
        "'" in value,      # 包含单引号
        '\n' in value,     # 包含换行
        '\r' in value,     # 包含回车
        '\t' in value,     # 包含制表符
        value.startswith('#'),  # 以#开头
        '=' in value,      # 包含等号
        value != value.strip(),  # 前后有空白
    ])
    
    if needs_quotes:
        # 转义内部的双引号和反斜杠
        escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped_value}"'
    
    return value

def create_complete_env_file():
    """创建完整的 .env 配置文件"""
    
    project_root = Path(__file__).parent.parent
    env_dist_path = project_root / "conf" / ".env.dist"
    env_path = project_root / "conf" / ".env"
    
    print("🔧 检查 .env 配置文件...")
    
    # 检查是否已存在 .env 文件
    if env_path.exists():
        print(f"✅ .env 文件已存在: {env_path}")
        
        # 读取现有配置
        with open(env_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # 读取模板配置
        with open(env_dist_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 检查是否需要更新
        template_lines = [line.split('=')[0] for line in template_content.split('\n') 
                         if line.strip() and not line.startswith('#') and '=' in line]
        existing_lines = [line.split('=')[0] for line in existing_content.split('\n') 
                         if line.strip() and not line.startswith('#') and '=' in line]
        
        missing_keys = set(template_lines) - set(existing_lines)
        
        if missing_keys:
            print(f"⚠️ 发现缺失的配置项 ({len(missing_keys)} 个): {', '.join(list(missing_keys)[:5])}{'...' if len(missing_keys) > 5 else ''}")
            print("🔄 更新 .env 文件...")
            
            # 备份现有文件
            backup_path = env_path.with_suffix('.env.backup')
            if backup_path.exists():
                backup_path.unlink()
            shutil.copy2(env_path, backup_path)
            print(f"📦 已备份原文件到: {backup_path}")
            
            # 合并配置
            merged_content = merge_env_configs(existing_content, template_content)
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
            
            print("✅ .env 文件已更新完成")
            print(f"📊 已添加 {len(missing_keys)} 个缺失的配置项")
        else:
            print("✅ .env 文件配置完整，无需更新")
        
        return True
    
    # 如果不存在 .env 文件，从模板创建
    print(f"📋 从模板创建 .env 文件...")
    
    if not env_dist_path.exists():
        print(f"❌ 配置模板文件不存在: {env_dist_path}")
        return False
    
    # 复制模板文件并生成默认配置
    with open(env_dist_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 生成带有默认值的配置
    env_content = generate_default_config(template_content)
    
    # 确保 conf 目录存在
    env_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入 .env 文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ 已创建完整的 .env 配置文件")
    print(f"📍 位置: {env_path}")
    print("\n🔧 请根据您的实际环境修改以下关键配置项:")
    print("   - LLM_PROVIDER: 选择您的大语言模型提供商 (deepseek/openai/zhipuai)")
    print("   - 对应的 API_KEY: 配置相应的 API 密钥")
    print("   - DASHBOARD_PASSWORD: 修改默认登录密码")
    print("   - 消息推送配置: 钉钉/企微/飞书 (可选)")
    print("   - 代码仓库配置: GitLab/GitHub (可选)")
    
    return True

def merge_env_configs(existing_content, template_content):
    """合并现有配置和模板配置"""
    
    # 解析现有配置
    existing_config = {}
    existing_comments = []
    
    for line in existing_content.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith('#') or not stripped_line:
            # 保留注释和空行
            existing_comments.append(line)
        elif '=' in stripped_line:
            key, value = stripped_line.split('=', 1)
            existing_config[key] = value
    
    # 生成合并后的配置
    merged_lines = []
    for line in template_content.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith('#') or not stripped_line:            # 保留模板中的注释和空行
            merged_lines.append(line)
        elif '=' in stripped_line:
            key, default_value = stripped_line.split('=', 1)
            # 使用现有值，如果不存在则使用模板中的默认值或增强的默认值
            if key in existing_config:
                value = existing_config[key]
            else:
                value = get_enhanced_default_value(key, default_value)
            escaped_value = escape_env_value(value)
            merged_lines.append(f"{key}={escaped_value}")
        else:
            merged_lines.append(line)
    
    return '\n'.join(merged_lines)

def generate_default_config(template_content):
    """生成带有合理默认值的配置"""
    
    # 生成配置内容
    config_lines = []
    for line in template_content.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith('#') or not stripped_line:
            # 保留注释和空行
            config_lines.append(line)
        elif '=' in stripped_line:
            key, template_value = stripped_line.split('=', 1)
            # 使用增强的默认值
            value = get_enhanced_default_value(key, template_value)
            escaped_value = escape_env_value(value)
            config_lines.append(f"{key}={escaped_value}")
        else:
            config_lines.append(line)
    
    return '\n'.join(config_lines)

def get_enhanced_default_value(key, template_value):
    """获取增强的默认值"""
    
    # 增强的默认值映射
    enhanced_defaults = {
        'SERVER_PORT': '5001',
        'TZ': 'Asia/Shanghai',
        'LLM_PROVIDER': 'deepseek',
        'DEEPSEEK_API_KEY': '',
        'DEEPSEEK_API_BASE_URL': 'https://api.deepseek.com',
        'DEEPSEEK_API_MODEL': 'deepseek-chat',
        'OPENAI_API_KEY': '',
        'OPENAI_API_BASE_URL': 'https://api.openai.com/v1',
        'OPENAI_API_MODEL': 'gpt-4o-mini',
        'ZHIPUAI_API_KEY': '',
        'ZHIPUAI_API_MODEL': 'GLM-4-Flash',
        'QWEN_API_KEY': '',
        'QWEN_API_BASE_URL': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'QWEN_API_MODEL': 'qwen-coder-plus',
        'OLLAMA_API_BASE_URL': 'http://host.docker.internal:11434',
        'OLLAMA_API_MODEL': 'deepseek-r1:latest',
        'SUPPORTED_EXTENSIONS': '.c,.cc,.cpp,.cs,.css,.go,.h,.java,.js,.jsx,.lua,.md,.php,.py,.sql,.ts,.tsx,.vue,.yml',
        'REVIEW_MAX_TOKENS': '10000',
        'REVIEW_STYLE': 'professional',
        'VERSION_TRACKING_ENABLED': '1',
        'REUSE_PREVIOUS_REVIEW_RESULT': '1',
        'VERSION_TRACKING_RETENTION_DAYS': '30',
        'DINGTALK_ENABLED': '0',
        'DINGTALK_WEBHOOK_URL': '',
        'WECOM_ENABLED': '0',
        'WECOM_WEBHOOK_URL': '',
        'FEISHU_ENABLED': '0',
        'FEISHU_WEBHOOK_URL': '',
        'EXTRA_WEBHOOK_ENABLED': '0',
        'EXTRA_WEBHOOK_URL': '',
        'LOG_FILE': 'log/app.log',
        'LOG_MAX_BYTES': '10485760',
        'LOG_BACKUP_COUNT': '3',
        'LOG_LEVEL': 'INFO',
        'REPORT_CRONTAB_EXPRESSION': '0 18 * * 1-5',
        'PUSH_REVIEW_ENABLED': '1',
        'MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED': '0',
        'DASHBOARD_USER': 'admin',
        'DASHBOARD_PASSWORD': 'admin123',
        'QUEUE_DRIVER': 'async',
        'SVN_CHECK_ENABLED': '0',
        'SVN_REPOSITORIES': '[]',
        'SVN_CHECK_CRONTAB': '*/30 * * * *',
        'SVN_CHECK_LIMIT': '100',
        'SVN_REVIEW_ENABLED': '1',
    }
    
    # 返回增强默认值或模板值
    return enhanced_defaults.get(key, template_value)

def create_directories():
    """创建必要的目录"""
    directories = ['data', 'log', 'conf', 'data/svn']
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 确保目录存在: {directory}")

def check_permissions():
    """检查文件权限"""
    try:
        # 检查写入权限
        test_file = Path("conf/.test_write")
        test_file.write_text("test")
        test_file.unlink()
        print("✅ 配置目录写入权限正常")
        return True
    except Exception as e:
        print(f"❌ 配置目录写入权限检查失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 AI-CodeReview 环境配置初始化 (增强版)")
    print("=" * 60)
    print("📋 解决 docker-compose 部署时 .env 数据不完整的问题")
    print("=" * 60)
    
    try:
        # 检查权限
        if not check_permissions():
            print("⚠️ 权限检查失败，但继续尝试初始化...")
        
        # 创建必要目录
        print("\n📁 创建必要目录...")
        create_directories()
        
        # 创建或更新配置文件
        print("\n⚙️ 处理配置文件...")
        success = create_complete_env_file()
        
        if success:
            print("\n🎉 环境配置初始化完成！")
            print("\n📚 下一步操作:")
            print("   1. 编辑 conf/.env 文件，配置您的 LLM API 密钥")
            print("   2. 根据需要配置消息推送和代码仓库访问")
            print("   3. 启动服务: docker-compose up -d")
            print("\n📖 详细配置说明请参考:")
            print("   - docs/deployment_guide.md (部署指南)")
            print("   - docs/faq.md (常见问题)")
            print("   - README.md (项目说明)")
            return True
        else:
            print("\n❌ 环境配置初始化失败")
            return False
    except Exception as e:
        print(f"\n💥 初始化过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
