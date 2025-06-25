#!/usr/bin/env python3
"""
Docker初始化诊断脚本
检查当前环境状态并诊断可能的问题
"""

import os
import sys
from pathlib import Path

def diagnose_environment():
    """诊断当前环境状态"""
    print("=" * 60)
    print("Docker 初始化环境诊断")
    print("=" * 60)
    
    # 1. 检查当前工作目录
    current_dir = Path.cwd()
    print(f"当前工作目录: {current_dir}")
    
    # 2. 检查关键路径是否存在
    important_paths = {
        './conf': '配置目录',
        './conf_templates': '模板目录 (如果存在)',
        './scripts': '脚本目录',
        './scripts/docker_init.py': 'Docker初始化脚本',
        './Dockerfile': 'Dockerfile',
        './docker-compose.yml': 'Docker Compose配置'
    }
    
    print("\n路径检查:")
    print("-" * 40)
    for path, description in important_paths.items():
        path_obj = Path(path)
        status = "✅ 存在" if path_obj.exists() else "❌ 不存在"
        path_type = ""
        if path_obj.exists():
            if path_obj.is_dir():
                path_type = " (目录)"
            elif path_obj.is_file():
                path_type = " (文件)"
        print(f"{status:<10} {path:<25} - {description}{path_type}")
    
    # 3. 检查配置文件内容
    conf_dir = Path('./conf')
    if conf_dir.exists():
        print(f"\n配置目录内容:")
        print("-" * 40)
        try:
            files = list(conf_dir.iterdir())
            if files:
                for file in sorted(files):
                    size = file.stat().st_size if file.is_file() else "目录"
                    print(f"  {file.name:<30} ({size})")
            else:
                print("  配置目录为空")
        except Exception as e:
            print(f"  无法读取配置目录: {e}")
    
    # 4. 检查模板目录内容（如果存在）
    template_dir = Path('./conf_templates')
    if template_dir.exists():
        print(f"\n模板目录内容:")
        print("-" * 40)
        try:
            files = list(template_dir.iterdir())
            if files:
                for file in sorted(files):
                    size = file.stat().st_size if file.is_file() else "目录"
                    print(f"  {file.name:<30} ({size})")
            else:
                print("  模板目录为空")
        except Exception as e:
            print(f"  无法读取模板目录: {e}")
    
    # 5. 检查环境变量
    print(f"\n重要环境变量:")
    print("-" * 40)
    important_env_vars = [
        'DOCKER_RUN_MODE',
        'TZ',
        'LOG_LEVEL',
        'LLM_TYPE',
        'API_KEY',
        'DEBUG'
    ]
    
    for var in important_env_vars:
        value = os.environ.get(var, '未设置')
        print(f"  {var:<20}: {value}")
    
    # 6. 检查Python环境
    print(f"\nPython环境信息:")
    print("-" * 40)
    print(f"  Python版本: {sys.version}")
    print(f"  Python路径: {sys.executable}")
    print(f"  当前用户: {os.environ.get('USER', os.environ.get('USERNAME', '未知'))}")
    
    # 7. 尝试运行docker_init.py的主要函数
    print(f"\n功能测试:")
    print("-" * 40)
    
    try:
        # 导入docker_init模块
        sys.path.insert(0, str(Path('./scripts')))
        import docker_init
        print("✅ docker_init模块导入成功")
        
        # 测试关键函数是否存在
        functions_to_test = [
            'ensure_config_files',
            'setup_supervisord_config', 
            'load_environment_variables',
            'create_required_directories',
            'validate_critical_config'
        ]
        
        for func_name in functions_to_test:
            if hasattr(docker_init, func_name):
                print(f"✅ 函数 {func_name} 存在")
            else:
                print(f"❌ 函数 {func_name} 不存在")
                
    except Exception as e:
        print(f"❌ docker_init模块导入失败: {e}")
    
    print("\n" + "=" * 60)
    return True

def suggest_fixes():
    """根据诊断结果提供修复建议"""
    print("修复建议:")
    print("=" * 60)
    
    suggestions = []
    
    # 检查基本目录结构
    if not Path('./conf').exists():
        suggestions.append("创建配置目录: mkdir conf")
    
    if not Path('./scripts/docker_init.py').exists():
        suggestions.append("检查docker_init.py脚本是否存在")
    
    # 检查模板文件
    template_dir = Path('./conf')
    required_templates = ['.env.dist', 'dashboard_config.py', 'prompt_templates.yml']
    missing_templates = []
    
    for template in required_templates:
        if not (template_dir / template).exists():
            missing_templates.append(template)
    
    if missing_templates:
        suggestions.append(f"缺少模板文件: {', '.join(missing_templates)}")
    
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
    else:
        print("未发现明显问题，可能需要更详细的日志来诊断")
    
    print("\n快速修复命令:")
    print("-" * 40)
    print("# 创建必要目录")
    print("mkdir -p conf log data data/svn")
    print("")
    print("# 如果在Docker环境中，检查路径映射")
    print("# 确保docker-compose.yml中的卷映射正确")
    print("")
    print("# 运行初始化脚本的详细模式")
    print("python scripts/docker_init.py")

if __name__ == '__main__':
    try:
        diagnose_environment()
        print()
        suggest_fixes()
    except Exception as e:
        print(f"诊断过程中出现错误: {e}")
        sys.exit(1)
