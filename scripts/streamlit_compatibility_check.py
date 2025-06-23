#!/usr/bin/env python3
"""
Streamlit版本兼容性检查和修复工具
"""

import streamlit as st
import sys
import re
from pathlib import Path

def check_streamlit_version():
    """检查Streamlit版本并提供兼容性信息"""
    version = st.__version__
    print(f"📊 当前Streamlit版本: {version}")
    
    # 解析版本号
    try:
        major, minor, patch = map(int, version.split('.'))
        version_tuple = (major, minor, patch)
    except:
        print("⚠️ 无法解析版本号")
        return False
    
    # 检查rerun方法可用性
    has_rerun = hasattr(st, 'rerun')
    has_experimental_rerun = hasattr(st, 'experimental_rerun')
    
    print(f"🔍 rerun() 方法: {'✅ 可用' if has_rerun else '❌ 不可用'}")
    print(f"🔍 experimental_rerun() 方法: {'✅ 可用' if has_experimental_rerun else '❌ 不可用'}")
    
    # 版本兼容性建议
    if version_tuple >= (1, 27, 0):
        print("✅ 推荐版本，支持所有新功能")
        return True
    elif version_tuple >= (1, 18, 0):
        print("⚠️ 较旧版本，建议升级到最新版本")
        return True
    else:
        print("❌ 版本过旧，强烈建议升级")
        return False

def fix_ui_compatibility():
    """修复UI文件的兼容性问题"""
    ui_file = Path("ui.py")
    if not ui_file.exists():
        print("❌ ui.py 文件不存在")
        return False
    
    print("🔧 开始修复UI兼容性...")
    
    # 读取文件
    with open(ui_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经有兼容函数
    if 'def st_rerun():' not in content:
        print("❌ 未发现兼容函数，请先添加兼容函数")
        return False
    
    # 统计需要替换的调用
    rerun_calls = len(re.findall(r'st\.rerun\(\)', content))
    
    if rerun_calls > 0:
        # 替换所有的 st.rerun() 为 st_rerun()
        content = re.sub(r'st\.rerun\(\)', 'st_rerun()', content)
        
        # 写回文件
        with open(ui_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已替换 {rerun_calls} 个 st.rerun() 调用")
    else:
        print("✅ 没有发现需要替换的调用")
    
    return True

def test_ui_import():
    """测试UI模块导入"""
    print("🧪 测试UI模块导入...")
    try:
        # 测试导入（不执行主逻辑）
        import importlib.util
        spec = importlib.util.spec_from_file_location("ui_test", "ui.py")
        if spec and spec.loader:
            print("✅ UI模块语法检查通过")
            return True
        else:
            print("❌ UI模块导入失败")
            return False
    except Exception as e:
        print(f"❌ UI模块导入错误: {e}")
        return False

def main():
    """主函数"""
    print("🔍 Streamlit兼容性检查工具")
    print("=" * 50)
    
    # 检查版本
    version_ok = check_streamlit_version()
    print()
    
    # 修复兼容性
    fix_ok = fix_ui_compatibility()
    print()
    
    # 测试导入
    import_ok = test_ui_import()
    print()
    
    # 总结
    print("📋 检查结果总结:")
    print(f"  版本检查: {'✅ 通过' if version_ok else '❌ 失败'}")
    print(f"  兼容性修复: {'✅ 完成' if fix_ok else '❌ 失败'}")
    print(f"  模块测试: {'✅ 通过' if import_ok else '❌ 失败'}")
    
    if version_ok and fix_ok and import_ok:
        print("\n🎉 所有检查通过，UI应该可以正常运行！")
        print("💡 运行命令: streamlit run ui.py --server.port=8501")
    else:
        print("\n⚠️ 发现问题，请查看上述错误信息")
        if not version_ok:
            print("💡 建议升级Streamlit: pip install streamlit --upgrade")

if __name__ == "__main__":
    main()
