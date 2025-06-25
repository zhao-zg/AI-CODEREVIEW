"""
快速测试脚本 - 验证数据库连接和关键功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """测试数据库连接"""
    try:
        from biz.service.review_service import ReviewService
        from datetime import datetime, timedelta
        
        print("🔗 测试数据库连接...")
        
        review_service = ReviewService()
        
        # 测试简单查询（不使用limit参数）
        one_week_ago = datetime.now() - timedelta(days=7)
        
        print(f"📅 查询最近一周的评审日志（从 {one_week_ago.strftime('%Y-%m-%d')} 开始）...")
        
        df = review_service.get_mr_review_logs(updated_at_gte=one_week_ago)
        
        if df is not None and len(df) > 0:
            print(f"✅ 数据库连接成功！找到 {len(df)} 条评审记录")
            print(f"📊 数据概览：")
            print(f"   - 列数：{len(df.columns)}")
            print(f"   - 行数：{len(df)}")
            if len(df) > 0:
                print(f"   - 最新记录：{df.iloc[0].get('created_at', 'N/A')}")
        else:
            print("✅ 数据库连接成功！暂无评审记录")
            
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def test_config_manager():
    """测试配置管理器"""
    try:
        from biz.utils.config_manager import ConfigManager
        
        print("⚙️ 测试配置管理器...")
        
        config_manager = ConfigManager()
        config = config_manager.get_env_config()
        
        if config:
            print(f"✅ 配置管理器正常！加载了 {len(config)} 项配置")
            
            # 显示几个关键配置
            key_configs = ['LLM_PROVIDER', 'SERVER_PORT', 'LOG_LEVEL']
            for key in key_configs:
                value = config.get(key, 'N/A')
                print(f"   - {key}: {value}")
        else:
            print("⚠️ 配置管理器运行正常，但未找到配置")
            
        return True
        
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 开始系统测试...")
    print("=" * 50)
    
    tests = [
        ("数据库连接", test_database_connection),
        ("配置管理器", test_config_manager),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 测试：{test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果：{passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关组件")
        return False

if __name__ == "__main__":
    main()
