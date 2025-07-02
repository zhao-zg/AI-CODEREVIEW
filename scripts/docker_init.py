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
    
    print("Docker 配置文件自动初始化...")
    
    # 配置文件路径
    conf_dir = Path('/app/conf')
    template_dir = Path('/app/conf_templates')
    
    # 确保配置目录存在
    conf_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"配置目录: {conf_dir}")
    print(f"模板目录: {template_dir}")
    
    # 必要的配置文件列表
    config_files = {
        '.env.dist': '环境变量模板文件',
        'dashboard_config.py': '仪表板配置文件',
        'prompt_templates.yml': '提示模板配置文件',
        'supervisord.all.conf': 'Supervisord统一配置'
    }
    
    missing_files = []
    
    # 检查配置文件是否存在，不存在则从模板复制
    for filename, description in config_files.items():
        config_file = conf_dir / filename
        template_file = template_dir / filename
        
        if not config_file.exists():
            if template_file.exists():
                print(f"从模板复制: {filename}")
                shutil.copy2(template_file, config_file)
                print(f"[OK] 已复制: {filename} ({description})")
            else:
                missing_files.append((filename, description))
                print(f"[ERROR] 缺失: {filename} ({description}) - 模板文件也不存在")
        else:
            print(f"[OK] 存在: {filename} ({description})")
    
    if missing_files:
        print(f"\n[WARNING] 发现 {len(missing_files)} 个无法从模板复制的配置文件")
        print("[INFO] 这些文件可能需要手动创建或检查模板目录")
        for filename, description in missing_files:
            print(f"   - {filename}: {description}")
    
    print("\n[OK] 配置文件初始化完成")
    
    # 特殊处理 .env 文件
    env_file = conf_dir / '.env'
    env_dist_file = template_dir / '.env.dist'
    
    if not env_file.exists() and env_dist_file.exists():
        print("从 conf_templates/.env.dist 创建默认 .env 文件...")
        shutil.copy2(env_dist_file, env_file)
        print("[OK] 已创建默认 .env 文件")
    
    return True

def setup_supervisord_config():
    """设置 supervisord 配置"""
    
    print("\n配置 supervisord...")
    
    supervisord_conf_dir = Path('/etc/supervisor/conf.d')
    supervisord_conf_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用统一配置（API + UI 在一个服务中）
    conf_filename = 'supervisord.all.conf'
    print("配置为统一服务模式（API + UI + 后台任务）")
    
    # 按优先级查找配置文件：运行时配置 -> 模板配置
    source_conf = None
    search_paths = [
        Path('/app/conf') / conf_filename,      # 运行时配置
        Path('/app/conf_templates') / conf_filename  # 模板配置
    ]
    
    for path in search_paths:
        if path.exists():
            source_conf = path
            print(f"使用配置文件: {source_conf}")
            break
    
    target_conf = supervisord_conf_dir / 'supervisord.conf'
    
    if source_conf and source_conf.exists():
        try:
            shutil.copy2(source_conf, target_conf)
            print(f"[OK] 复制配置文件: {source_conf} -> {target_conf}")
            return True
        except Exception as e:
            print(f"[ERROR] 复制配置文件失败: {e}")
            return False
    else:
        print(f"[ERROR] 找不到 supervisord 配置文件: {conf_filename}")
        print("[INFO] 尝试创建默认配置...")
        
        # 创建默认的 supervisord 配置
        try:
            default_config = create_default_supervisord_config()
            with open(target_conf, 'w', encoding='utf-8') as f:
                f.write(default_config)
            print(f"[OK] 已创建默认配置: {target_conf}")
            return True
        except Exception as e:
            print(f"[ERROR] 创建默认配置失败: {e}")
            return False

def create_default_supervisord_config():
    """创建默认的 supervisord 配置 - 单服务模式"""
    
    return """[supervisord]
nodaemon=true
user=root

[program:api]
command=python /app/api.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/api.err.log
stdout_logfile=/app/log/api.out.log
environment=PYTHONPATH="/app"

[program:ui]
command=python /app/ui.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/ui.err.log
stdout_logfile=/app/log/ui.out.log
environment=PYTHONPATH="/app"
"""

def load_environment_variables():
    """加载环境变量"""
    
    print("\n加载环境变量...")
    
    env_file = Path('/app/conf/.env')
    
    if not env_file.exists():
        print("[WARNING] .env 文件不存在，跳过环境变量加载")
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
        
        print(f"[OK] 加载了 {loaded_count} 个环境变量")
        return True
        
    except Exception as e:
        print(f"[ERROR] 加载环境变量失败: {e}")
        return False

def create_required_directories():
    """创建必要的目录"""
    
    print("\n创建必要的目录...")
    
    required_dirs = [
        '/app/log',
        '/app/data',
        '/app/data/svn'
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"[OK] 确保目录存在: {dir_path}")

def validate_critical_config():
    """验证关键配置"""
    
    print("\n验证关键配置...")
    
    # 检查必要的目录是否存在
    required_dirs = [
        '/app/log',
        '/app/data',
        '/app/conf'
    ]
    
    dir_warnings = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            dir_warnings.append(f"目录不存在: {dir_path}")
        else:
            print(f"[OK] 目录存在: {dir_path}")
    
    # 检查关键文件是否存在（非必需，只是警告）
    important_files = {
        '/app/conf/.env': '环境变量配置文件',
        '/app/api.py': 'API 主程序',
        '/app/ui.py': 'UI 主程序'
    }
    
    file_warnings = []
    for file_path, description in important_files.items():
        if not Path(file_path).exists():
            file_warnings.append(f"{description}不存在: {file_path}")
        else:
            print(f"[OK] {description}: {file_path}")
    
    # 检查环境变量（可选）
    optional_env_vars = {
        'DOCKER_RUN_MODE': '运行模式',
        'TZ': '时区设置',
        'LOG_LEVEL': '日志级别'
    }
    
    env_info = []
    for key, description in optional_env_vars.items():
        value = os.environ.get(key, '未设置')
        print(f"[INFO] {key} ({description}): {value}")
        if value == '未设置':
            env_info.append(f"{key} ({description}) 使用默认值")
    
    # 汇总警告信息
    all_warnings = dir_warnings + file_warnings
    
    if all_warnings:
        print(f"\n[WARNING] 发现 {len(all_warnings)} 个问题:")
        for warning in all_warnings:
            print(f"   - {warning}")
    
    if env_info:
        print(f"\n[INFO] 环境变量信息:")
        for info in env_info:
            print(f"   - {info}")
    
    # 只有在关键目录缺失时才返回 False
    return len(dir_warnings) == 0

def main():
    """主函数"""
    
    print("Docker 配置初始化开始...")
    print("=" * 50)
    
    success = True
    
    # 1. 确保配置文件存在
    if not ensure_config_files():
        print("\n[ERROR] 配置文件初始化失败")
        success = False
    
    # 2. 创建必要目录
    create_required_directories()
    
    # 3. 加载环境变量
    if not load_environment_variables():
        print("\n[ERROR] 环境变量加载失败")
        success = False
    
    # 4. 设置 supervisord 配置
    if not setup_supervisord_config():
        print("\n[ERROR] supervisord 配置失败")
        success = False
    
    # 5. 验证关键配置
    config_ok = validate_critical_config()
    
    print("\n" + "=" * 50)
    
    if success and config_ok:
        print("[OK] Docker 配置初始化成功完成！")
        print("[INFO] 准备启动服务...")
        return 0
    else:
        print("[ERROR] Docker 配置初始化存在问题")
        if not config_ok:
            print("[WARNING] 配置验证失败，但仍将尝试启动服务")
            print("[INFO] 请在启动后通过环境变量或 UI 界面完善配置")
            return 0  # 允许继续启动，但会有警告
        else:
            print("[ERROR] 严重错误，无法启动服务")
            return 1

if __name__ == '__main__':
    sys.exit(main())
