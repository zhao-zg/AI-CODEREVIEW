# -*- coding: utf-8 -*-
"""UI组件入口模块 - 统一管理和导出所有UI组件"""

# 导入所有模块
from .data_processor import DataProcessor
from .analytics import AnalyticsEngine, DisplayConfig
from .ui_components import UIComponents, UITheme
from .export_utils import DataExporter
from .data_display import display_manager, display_version_tracking_data, display_legacy_data

# 版本信息
__version__ = "2.0.0"
__author__ = "AI-CodeReview-Gitlab Team"

# 导出主要类和函数
__all__ = [
    # 主要功能函数
    'display_version_tracking_data',
    'display_legacy_data',
    
    # 核心类
    'DataProcessor',
    'AnalyticsEngine',
    'UIComponents',
    'DataExporter',
    
    # 配置类
    'DisplayConfig',
    'UITheme',
    
    # 管理器
    'display_manager'
]

# 模块信息
MODULE_INFO = {
    'name': 'UI Components Module',
    'version': __version__,
    'description': '数据分析和展示UI组件模块，支持多数据源分析',
    'modules': {
        'data_processor': '数据处理模块 - 负责数据预处理、清洗和标准化',
        'analytics': '统计分析模块 - 负责数据统计分析和图表生成',
        'ui_components': 'UI组件模块 - 提供通用的UI组件和界面元素',
        'export_utils': '导出工具模块 - 负责数据导出功能',
        'data_display': '数据显示模块 - 主要的数据显示和管理功能'
    },
    'features': [
        '✅ 支持SVN、GitLab MR、Push多数据源',
        '✅ 模块化架构，便于维护和扩展',
        '✅ 优化的用户界面和交互体验',
        '✅ 丰富的数据分析和可视化功能',
        '✅ 多格式数据导出支持',
        '✅ 实时数据处理和筛选',
        '✅ 响应式设计和主题配置'
    ]
}

def get_module_info():
    """获取模块信息"""
    return MODULE_INFO

def print_module_info():
    """打印模块信息"""
    print(f"\n🎯 {MODULE_INFO['name']} v{MODULE_INFO['version']}")
    print(f"📝 {MODULE_INFO['description']}\n")
    
    print("📦 包含模块:")
    for module, desc in MODULE_INFO['modules'].items():
        print(f"  • {module}: {desc}")
    
    print("\n🚀 主要特性:")
    for feature in MODULE_INFO['features']:
        print(f"  {feature}")
    
    print(f"\n👨‍💻 作者: {__author__}")
    print("=" * 60)

# 初始化检查
def check_dependencies():
    """检查依赖项"""
    required_packages = [
        'streamlit',
        'pandas', 
        'plotly',
        'openpyxl'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print(f"💡 请运行: pip install {' '.join(missing_packages)}")
        return False
    else:
        print("✅ 所有依赖项检查通过")
        return True

# 模块初始化时自动检查
if __name__ == "__main__":
    print_module_info()
    check_dependencies()
