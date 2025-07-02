#!/usr/bin/env python3
"""
AI-CodeReview UI 健康检查脚本
用于日常维护和问题排查
"""

import sys
import json
import importlib.util
import traceback
from pathlib import Path

def check_imports():
    """检查关键模块导入"""
    print("🔍 检查模块导入...")
    try:
        import streamlit as st
        print(f"✅ Streamlit {st.__version__}")
        
        # 检查项目模块
        sys.path.append(str(Path(__file__).parent))
        
        from ui_components.pages import env_management_page, data_analysis_page
        print("✅ ui_components.pages 导入成功")
        
        from biz.utils.config_manager import ConfigManager
        print("✅ ConfigManager 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def check_config_manager():
    """检查配置管理器功能"""
    print("\n🔍 检查配置管理器...")
    try:
        from biz.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        # 检查关键方法存在
        if not hasattr(config_manager, 'save_env_config'):
            print("❌ ConfigManager.save_env_config 方法不存在")
            return False
        
        if not hasattr(config_manager, 'get_env_config'):
            print("❌ ConfigManager.get_env_config 方法不存在")
            return False
        
        # 尝试获取配置
        env_config = config_manager.get_env_config()
        print("✅ 环境配置获取成功")
        
        # 检查 SVN 配置
        svn_config = env_config.get("SVN_REPOSITORIES", "[]")
        if svn_config:
            try:
                svn_repos = json.loads(svn_config) if svn_config.strip() else []
                print(f"✅ SVN 仓库配置解析成功，包含 {len(svn_repos)} 个仓库")
            except json.JSONDecodeError:
                print("⚠️ SVN 仓库配置 JSON 格式错误")
        else:
            print("ℹ️ SVN 仓库配置为空")
        
        return True
    except Exception as e:
        print(f"❌ 配置管理器检查失败: {e}")
        traceback.print_exc()
        return False

def check_pages_structure():
    """检查页面结构"""
    print("\n🔍 检查页面结构...")
    try:
        pages_file = Path(__file__).parent / "ui_components" / "pages.py"
        if not pages_file.exists():
            print("❌ pages.py 文件不存在")
            return False
        
        with open(pages_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键函数
        key_functions = [
            'env_management_page',
            'data_analysis_page'
        ]
        
        for func in key_functions:
            if f"def {func}" in content:
                print(f"✅ 函数 {func} 存在")
            else:
                print(f"❌ 函数 {func} 不存在")
                return False
        
        # 检查表单提交按钮
        submit_count = content.count('st.form_submit_button')
        print(f"✅ 发现 {submit_count} 个表单提交按钮")
        
        # 检查 SVN 相关代码
        if 'svn_repos_session' in content:
            print("✅ SVN 会话状态管理存在")
        else:
            print("⚠️ SVN 会话状态管理可能缺失")
        
        if 'save_env_config' in content:
            print("✅ 使用正确的配置保存方法")
        else:
            print("⚠️ 配置保存方法可能有问题")
        
        return True
    except Exception as e:
        print(f"❌ 页面结构检查失败: {e}")
        return False

def check_ui_service():
    """检查 UI 服务状态"""
    print("\n🔍 检查 UI 服务...")
    try:
        import requests
        response = requests.get('http://localhost:5002', timeout=5)
        if response.status_code == 200:
            print("✅ UI 服务运行正常 (HTTP 200)")
            return True
        else:
            print(f"⚠️ UI 服务响应异常 (HTTP {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ UI 服务未启动或无法连接")
        return False
    except requests.exceptions.Timeout:
        print("❌ UI 服务响应超时")
        return False
    except ImportError:
        print("⚠️ requests 模块未安装，跳过服务检查")
        return True
    except Exception as e:
        print(f"❌ UI 服务检查失败: {e}")
        return False

def main():
    """主检查流程"""
    print("🚀 AI-CodeReview UI 健康检查")
    print("=" * 50)
    
    checks = [
        ("模块导入", check_imports),
        ("配置管理器", check_config_manager),
        ("页面结构", check_pages_structure),
        ("UI 服务", check_ui_service)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{'='*20} {name} {'='*20}")
        result = check_func()
        results.append((name, result))
    
    print("\n" + "="*50)
    print("📊 健康检查总结:")
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有检查通过，系统状态良好！")
        return 0
    else:
        print("\n⚠️ 存在问题，请检查上述失败项目")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
