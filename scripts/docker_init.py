#!/usr/bin/env python3
"""
Docker 配置文件自动初始化脚本
确保容器启动时所有必要的配置文件都存在并正确配置
"""

import os
import sys
import shutil
from pathlib import Path

def ensure_config_files():
    """确保所有必要的配置文件都存在"""
    
    print("🐳 Docker 配置文件自动初始化...")
    
    # 配置文件路径
    conf_dir = Path('/app/conf')
      # 必要的配置文件列表
    config_files = {
        '.env.dist': '环境变量模板文件',
        '.env': '环境变量配置文件',
        'dashboard_config.py': '仪表板配置文件',
        'prompt_templates.yml': '提示模板配置文件',
        'supervisord.app.conf': 'Supervisord应用配置',
        'supervisord.worker.conf': 'Supervisord工作者配置',
        'supervisord.all.conf': 'Supervisord统一配置'
    }
    
    missing_files = []
    
    # 检查必要文件是否存在
    for filename, description in config_files.items():
        file_path = conf_dir / filename
        if not file_path.exists():
            missing_files.append((filename, description))
            print(f"❌ 缺失: {filename} ({description})")
        else:
            print(f"✅ 存在: {filename} ({description})")
    
    if missing_files:
        print(f"\n⚠️  发现 {len(missing_files)} 个缺失的配置文件")
        return False
    
    print("\n✅ 所有必要的配置文件都存在")
    
    # 特殊处理 .env 文件
    env_file = conf_dir / '.env'
    env_dist_file = conf_dir / '.env.dist'
    
    if not env_file.exists() and env_dist_file.exists():
        print("🔄 从 .env.dist 创建默认 .env 文件...")
        shutil.copy2(env_dist_file, env_file)
        print("✅ 已创建默认 .env 文件")
    
    return True

def setup_supervisord_config():
    """设置 supervisord 配置"""
    
    print("\n🔧 配置 supervisord...")
    
    # 确定运行模式 (默认为 app)
    run_mode = os.environ.get('DOCKER_RUN_MODE', 'app')
    
    supervisord_conf_dir = Path('/etc/supervisor/conf.d')
    supervisord_conf_dir.mkdir(parents=True, exist_ok=True)
    
    if run_mode == 'worker':
        source_conf = Path('/app/conf/supervisord.worker.conf')
        print("📋 配置为 Worker 模式")
    elif run_mode == 'all':
        source_conf = Path('/app/conf/supervisord.all.conf')
        print("📋 配置为 All-in-One 模式（API + UI + 后台任务）")
    else:
        source_conf = Path('/app/conf/supervisord.app.conf')
        print("📋 配置为 App 模式")
    
    target_conf = supervisord_conf_dir / 'supervisord.conf'
    
    if source_conf.exists():
        shutil.copy2(source_conf, target_conf)
        print(f"✅ 复制配置文件: {source_conf} -> {target_conf}")
    else:
        print(f"❌ 源配置文件不存在: {source_conf}")
        return False
    
    return True

def load_environment_variables():
    """加载环境变量"""
    
    print("\n🌱 加载环境变量...")
    
    env_file = Path('/app/conf/.env')
    
    if not env_file.exists():
        print("⚠️  .env 文件不存在，跳过环境变量加载")
        return True
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        loaded_count = 0
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # 只设置还未设置的环境变量
                if key not in os.environ:
                    os.environ[key] = value
                    loaded_count += 1
        
        print(f"✅ 加载了 {loaded_count} 个环境变量")
        return True
        
    except Exception as e:
        print(f"❌ 加载环境变量失败: {e}")
        return False

def create_required_directories():
    """创建必要的目录"""
    
    print("\n📁 创建必要的目录...")
    
    required_dirs = [
        '/app/log',
        '/app/data',
        '/app/data/svn'
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ 确保目录存在: {dir_path}")

def validate_critical_config():
    """验证关键配置"""
    
    print("\n🔍 验证关键配置...")
    
    critical_configs = {
        'LLM_PROVIDER': '大语言模型提供商',
        'SERVER_PORT': '服务端口',
        'LOG_LEVEL': '日志级别'
    }
    
    warnings = []
    
    for key, description in critical_configs.items():
        value = os.environ.get(key)
        if not value:
            warnings.append(f"{key} ({description}) 未配置")
        else:
            print(f"✅ {key}: {value}")
    
    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个配置警告:")
        for warning in warnings:
            print(f"   - {warning}")
        print("\n💡 请检查 .env 文件并配置相应的值")
    
    return len(warnings) == 0

def main():
    """主函数"""
    
    print("🚀 Docker 配置初始化开始...")
    print("=" * 50)
    
    success = True
    
    # 1. 确保配置文件存在
    if not ensure_config_files():
        print("\n❌ 配置文件初始化失败")
        success = False
    
    # 2. 创建必要目录
    create_required_directories()
    
    # 3. 加载环境变量
    if not load_environment_variables():
        print("\n❌ 环境变量加载失败")
        success = False
    
    # 4. 设置 supervisord 配置
    if not setup_supervisord_config():
        print("\n❌ supervisord 配置失败")
        success = False
    
    # 5. 验证关键配置
    config_ok = validate_critical_config()
    
    print("\n" + "=" * 50)
    
    if success and config_ok:
        print("🎉 Docker 配置初始化成功完成！")
        print("🚀 准备启动服务...")
        return 0
    else:
        print("❌ Docker 配置初始化存在问题")
        if not config_ok:
            print("⚠️  配置验证失败，但仍将尝试启动服务")
            print("💡 请在启动后通过环境变量或 UI 界面完善配置")
            return 0  # 允许继续启动，但会有警告
        else:
            print("💥 严重错误，无法启动服务")
            return 1

if __name__ == '__main__':
    sys.exit(main())
