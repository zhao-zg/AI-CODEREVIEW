#!/usr/bin/env python3
"""
独立测试配置解析功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biz.utils.config_manager import ConfigManager

# 安全的整数转换，处理包含注释的配置值
def safe_int(value, default=0):
    """安全的整数转换，处理包含注释的配置值"""
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            # 移除行内注释
            if '#' in value:
                value = value.split('#')[0].strip()
            # 移除引号
            value = value.strip().strip('"\'')
            return int(value)
        return default
    except (ValueError, TypeError):
        return default

def test_config_parsing():
    """测试配置解析"""
    print("🧪 测试配置解析修复...")
    
    config_manager = ConfigManager()
    dashboard_config = config_manager.get_dashboard_config()
    
    print(f"📊 仪表板配置项数量: {len(dashboard_config)}")
    
    # 测试关键配置项
    test_keys = [
        "MAX_RECORDS_PER_PAGE", 
        "DEFAULT_CHART_HEIGHT", 
        "CACHE_TTL_MINUTES", 
        "AUTO_REFRESH_INTERVAL"
    ]
    
    for key in test_keys:
        value = dashboard_config.get(key)
        print(f"   {key}: {value} (类型: {type(value).__name__})")
        
        # 测试安全整数转换
        safe_value = safe_int(value, 0)
        print(f"   -> safe_int转换: {safe_value}")
    
    print("\n✅ 配置解析测试完成!")
    
    # 测试是否还会出现ValueError
    try:
        int_value = int(dashboard_config.get("MAX_RECORDS_PER_PAGE", 100))
        print(f"✅ 直接int()转换成功: {int_value}")
    except ValueError as e:
        print(f"❌ 直接int()转换失败: {e}")
        print("💡 但使用safe_int()可以安全处理这种情况")

if __name__ == "__main__":
    test_config_parsing()
