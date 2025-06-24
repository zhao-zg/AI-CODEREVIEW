#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI模块化系统测试脚本"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_module_imports():
    """测试模块导入"""
    print("🔧 测试模块导入...")
    
    try:
        # 测试核心模块导入
        from ui_components.data_processor import DataProcessor
        from ui_components.analytics import AnalyticsEngine, DisplayConfig
        from ui_components.ui_components import UIComponents, UITheme
        from ui_components.export_utils import DataExporter
        from ui_components.data_display import DataDisplayManager, display_version_tracking_data
        
        print("✅ 所有核心模块导入成功")
        
        # 测试模块初始化
        processor = DataProcessor()
        analytics = AnalyticsEngine()
        ui = UIComponents()
        exporter = DataExporter()
        manager = DataDisplayManager()
        
        print("✅ 所有模块实例化成功")
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 模块初始化失败: {e}")
        return False

def test_module_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能...")
    
    try:
        import pandas as pd
        from ui_components.data_processor import DataProcessor
        
        # 创建测试数据
        test_data = pd.DataFrame({
            'svn_author': ['user1', 'user2'],
            'svn_message': ['commit1', 'commit2'],
            'svn_date': [1640995200, 1641081600],
            'repository': ['repo1', 'repo2'],
            'score': [4.5, 3.8]
        })
        
        # 测试数据处理
        processor = DataProcessor()
        processed_data = processor.preprocess_dataframe(test_data)
        
        print("✅ 数据处理功能正常")
        
        # 测试数据摘要
        summary = processor.get_data_summary(processed_data)
        print(f"✅ 数据摘要生成成功: {summary['total_records']} 条记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        return False

def test_configuration():
    """测试配置"""
    print("\n⚙️ 测试配置...")
    
    try:
        from ui_components.analytics import DisplayConfig
        from ui_components.ui_components import UITheme
        
        # 测试颜色配置
        config = DisplayConfig()
        theme = UITheme()
        
        print(f"✅ 颜色配置加载成功: {len(config.COLOR_SCALES)} 个配色方案")
        print(f"✅ 主题配置加载成功: {len(theme.ICONS)} 个图标")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_module_info():
    """测试模块信息"""
    print("\n📋 测试模块信息...")
    
    try:
        from ui_components import get_module_info, check_dependencies
        
        # 获取模块信息
        info = get_module_info()
        print(f"✅ 模块信息: {info['name']} v{info['version']}")
        print(f"✅ 包含 {len(info['modules'])} 个子模块")
        print(f"✅ 提供 {len(info['features'])} 个主要特性")
        
        # 检查依赖
        deps_ok = check_dependencies()
        if deps_ok:
            print("✅ 所有依赖项检查通过")
        else:
            print("⚠️ 部分依赖项缺失")
        
        return True
        
    except Exception as e:
        print(f"❌ 模块信息测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 UI模块化系统测试开始")
    print("=" * 50)
    
    tests = [
        test_module_imports,
        test_module_functionality, 
        test_configuration,
        test_module_info
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！UI模块化系统运行正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关模块")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
