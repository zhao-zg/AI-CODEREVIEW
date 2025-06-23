#!/usr/bin/env python3
"""
AI-Codereview-Gitlab 项目验证脚本
用于验证项目修复后的状态
"""

import os
import sys
import importlib.util
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    print("🐍 Python版本检查...")
    version = sys.version_info
    print(f"   当前版本: {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 12:
        print("   ✅ Python版本符合要求 (3.12+)")
        return True
    else:
        print("   ❌ Python版本不符合要求，需要 3.12+")
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n📦 依赖包检查...")
    
    required_packages = [
        ('streamlit', 'streamlit'),
        ('pandas', 'pandas'),
        ('matplotlib', 'matplotlib'),
        ('python-dotenv', 'dotenv'),
        ('pyyaml', 'yaml')
    ]
    
    missing_packages = []
    for display_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"   ✅ {display_name}")
        except ImportError:
            print(f"   ❌ {display_name} (未安装)")
            missing_packages.append(display_name)
    
    return len(missing_packages) == 0

def check_config_files():
    """检查配置文件"""
    print("\n⚙️ 配置文件检查...")
    
    config_files = [
        'conf/.env.dist',
        'biz/utils/config_manager.py',
        'ui.py',
        'requirements.txt'
    ]
    
    all_exist = True
    for file_path in config_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} (不存在)")
            all_exist = False
    
    return all_exist

def check_ui_syntax():
    """检查UI文件语法"""
    print("\n🔍 UI文件语法检查...")
    
    try:
        with open('ui.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试编译
        compile(content, 'ui.py', 'exec')
        print("   ✅ ui.py 语法检查通过")
        return True
    except SyntaxError as e:
        print(f"   ❌ ui.py 语法错误: {e}")
        return False
    except Exception as e:
        print(f"   ❌ ui.py 检查失败: {e}")
        return False

def check_env_config():
    """检查环境变量配置"""
    print("\n🌍 环境变量配置检查...")
    
    try:
        from biz.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        env_config = config_manager.get_env_config()
        
        # 检查关键配置项
        required_configs = [
            'LLM_PROVIDER',
            'VERSION_TRACKING_ENABLED',
            'LOG_LEVEL',
            'REDIS_HOST',
            'REDIS_PORT'
        ]
        
        missing_configs = []
        for config_key in required_configs:
            if config_key in env_config:
                print(f"   ✅ {config_key}")
            else:
                print(f"   ⚠️ {config_key} (在模板中但未配置)")
                missing_configs.append(config_key)
        
        print(f"   📊 总配置项: {len(env_config)}")
        print(f"   📋 已配置项: {len([v for v in env_config.values() if v])}")
        
        return True
    except Exception as e:
        print(f"   ❌ 环境变量配置检查失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 AI-Codereview-Gitlab 项目验证开始...")
    print("=" * 50)
    
    # 检查项目根目录
    if not os.path.exists('ui.py'):
        print("❌ 请在项目根目录下运行此脚本")
        sys.exit(1)
    
    checks = [
        check_python_version,
        check_dependencies,
        check_config_files,
        check_ui_syntax,
        check_env_config
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        if check():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 验证结果: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("✅ 所有检查通过！项目状态良好，可以正常使用。")
        print("\n💡 启动建议:")
        print("   运行命令: streamlit run ui.py --server.port 8501")
        print("   访问地址: http://localhost:8501")
    else:
        print("⚠️ 部分检查未通过，请查看上述详细信息并进行修复。")
    
    print("\n🏁 验证完成!")

if __name__ == "__main__":
    main()
