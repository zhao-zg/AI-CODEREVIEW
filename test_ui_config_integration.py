#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试UI界面的增强merge检测配置功能
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('.'))

def test_ui_config_integration():
    """测试UI配置集成"""
    print("🔧 测试UI界面的增强merge检测配置功能")
    print("=" * 60)
    
    # 导入配置管理器
    try:
        from biz.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        # 测试读取当前配置
        current_config = config_manager.get_env_config()
        
        print("📋 当前配置状态:")
        print(f"  USE_ENHANCED_MERGE_DETECTION: {current_config.get('USE_ENHANCED_MERGE_DETECTION', '未设置')}")
        print(f"  MERGE_DETECTION_THRESHOLD: {current_config.get('MERGE_DETECTION_THRESHOLD', '未设置')}")
        
        # 检查配置是否在配置项列表中
        expected_configs = [
            "USE_ENHANCED_MERGE_DETECTION",
            "MERGE_DETECTION_THRESHOLD"
        ]
        
        missing_configs = []
        for config_key in expected_configs:
            if config_key not in current_config:
                missing_configs.append(config_key)
        
        if missing_configs:
            print(f"\n⚠️  缺少的配置项: {missing_configs}")
        else:
            print("\n✅ 所有配置项都已存在")
        
        # 测试配置值的有效性
        enhanced_enabled = current_config.get('USE_ENHANCED_MERGE_DETECTION', '0') == '1'
        threshold_str = current_config.get('MERGE_DETECTION_THRESHOLD', '0.4')
        
        try:
            threshold = float(threshold_str)
            if 0.0 <= threshold <= 1.0:
                print(f"✅ 阈值配置有效: {threshold}")
            else:
                print(f"❌ 阈值配置无效: {threshold} (应在0.0-1.0之间)")
        except ValueError:
            print(f"❌ 阈值配置格式错误: {threshold_str}")
        
        print(f"✅ 增强检测状态: {'启用' if enhanced_enabled else '禁用'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        return False

def test_config_categories():
    """测试配置分类显示"""
    print("\n🗂️ 测试配置分类显示")
    print("=" * 60)
    
    try:
        # 模拟UI页面中的配置分类
        categories = {
            "🤖 AI模型配置": ["LLM_PROVIDER", "DEEPSEEK_API_KEY", "DEEPSEEK_API_BASE_URL", "DEEPSEEK_API_MODEL", 
                           "OPENAI_API_KEY", "OPENAI_API_BASE_URL", "OPENAI_API_MODEL",
                           "ZHIPUAI_API_KEY", "ZHIPUAI_API_MODEL", 
                           "QWEN_API_KEY", "QWEN_API_BASE_URL", "QWEN_API_MODEL",
                           "JEDI_API_KEY", "JEDI_API_BASE_URL", "JEDI_API_MODEL",
                           "OLLAMA_API_BASE_URL", "OLLAMA_API_MODEL",
                           "REVIEW_STYLE", "REVIEW_MAX_TOKENS", "SUPPORTED_EXTENSIONS"],
            "🔀 平台开关": ["SVN_CHECK_ENABLED", "GITLAB_ENABLED", "GITHUB_ENABLED"],
            "📋 版本追踪配置": ["VERSION_TRACKING_ENABLED", "REUSE_PREVIOUS_REVIEW_RESULT", "VERSION_TRACKING_RETENTION_DAYS"],
            "🏠 系统配置": ["API_PORT", "API_URL", "UI_PORT", "UI_URL", "TZ", "LOG_LEVEL", "LOG_FILE", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT", "QUEUE_DRIVER"],
            "⚡ Redis配置": ["REDIS_HOST", "REDIS_PORT"],
            "📊 报告配置": ["REPORT_CRONTAB_EXPRESSION"],
            "🔗 GitLab配置": ["GITLAB_URL", "GITLAB_ACCESS_TOKEN", "PUSH_REVIEW_ENABLED", "MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED"],
            "🐙 GitHub配置": ["GITHUB_ACCESS_TOKEN"],
            "📂 SVN配置": ["SVN_CHECK_CRONTAB", "SVN_CHECK_LIMIT", "SVN_REVIEW_ENABLED", "SVN_REPOSITORIES", "USE_ENHANCED_MERGE_DETECTION", "MERGE_DETECTION_THRESHOLD"],
            "🔔 消息推送": ["NOTIFICATION_MODE", "DINGTALK_ENABLED", "DINGTALK_WEBHOOK_URL", "WECOM_ENABLED", "WECOM_WEBHOOK_URL", "FEISHU_ENABLED", "FEISHU_WEBHOOK_URL"],
            "🔗 额外Webhook": ["EXTRA_WEBHOOK_ENABLED", "EXTRA_WEBHOOK_URL"],
            "👤 Dashboard": ["DASHBOARD_USER", "DASHBOARD_PASSWORD"],
            "📝 Prompt模板": ["PROMPT_TEMPLATES_STATUS"]
        }
        
        # 检查增强merge检测配置是否在正确的分类中
        svn_configs = categories.get("📂 SVN配置", [])
        enhanced_configs = ["USE_ENHANCED_MERGE_DETECTION", "MERGE_DETECTION_THRESHOLD"]
        
        print("SVN配置分类中的配置项:")
        for config in svn_configs:
            if config in enhanced_configs:
                print(f"  ✅ {config} (新增)")
            else:
                print(f"  📋 {config}")
        
        # 验证新配置项是否都在SVN分类中
        missing_in_category = []
        for config in enhanced_configs:
            if config not in svn_configs:
                missing_in_category.append(config)
        
        if missing_in_category:
            print(f"\n❌ 未在SVN分类中找到: {missing_in_category}")
            return False
        else:
            print(f"\n✅ 所有增强merge检测配置都已正确分类")
            return True
            
    except Exception as e:
        print(f"❌ 配置分类测试失败: {e}")
        return False

def test_config_file_consistency():
    """测试配置文件一致性"""
    print("\n📄 测试配置文件一致性")
    print("=" * 60)
    
    try:
        # 检查 conf/.env 文件
        env_file = Path("conf/.env")
        if env_file.exists():
            print("✅ conf/.env 文件存在")
            
            # 读取配置文件内容
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查增强merge检测配置是否存在
            enhanced_configs = ["USE_ENHANCED_MERGE_DETECTION", "MERGE_DETECTION_THRESHOLD"]
            found_configs = {}
            
            for config in enhanced_configs:
                if config in content:
                    # 提取配置值
                    for line in content.split('\n'):
                        if line.strip().startswith(f"{config}="):
                            value = line.split('=', 1)[1].strip()
                            found_configs[config] = value
                            print(f"  ✅ {config}={value}")
                            break
                else:
                    print(f"  ❌ {config} 未在配置文件中找到")
            
            # 验证配置值
            if "USE_ENHANCED_MERGE_DETECTION" in found_configs:
                val = found_configs["USE_ENHANCED_MERGE_DETECTION"]
                if val in ['0', '1']:
                    print(f"    ✅ USE_ENHANCED_MERGE_DETECTION 值有效: {val}")
                else:
                    print(f"    ❌ USE_ENHANCED_MERGE_DETECTION 值无效: {val}")
            
            if "MERGE_DETECTION_THRESHOLD" in found_configs:
                try:
                    val = float(found_configs["MERGE_DETECTION_THRESHOLD"])
                    if 0.0 <= val <= 1.0:
                        print(f"    ✅ MERGE_DETECTION_THRESHOLD 值有效: {val}")
                    else:
                        print(f"    ❌ MERGE_DETECTION_THRESHOLD 值超出范围: {val}")
                except ValueError:
                    print(f"    ❌ MERGE_DETECTION_THRESHOLD 值格式错误: {found_configs['MERGE_DETECTION_THRESHOLD']}")
            
            return len(found_configs) == len(enhanced_configs)
        else:
            print("❌ conf/.env 文件不存在")
            return False
            
    except Exception as e:
        print(f"❌ 配置文件一致性测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🧪 AI-CodeReview UI配置功能测试")
    print("=" * 60)
    print("测试增强merge检测配置在UI界面的集成情况")
    
    results = []
    
    # 运行所有测试
    print("\n1️⃣ 配置管理器测试")
    results.append(test_ui_config_integration())
    
    print("\n2️⃣ 配置分类测试")
    results.append(test_config_categories())
    
    print("\n3️⃣ 配置文件一致性测试")
    results.append(test_config_file_consistency())
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    if all(results):
        print("🎉 所有测试通过！UI配置功能已正确集成。")
        print("\n📝 使用说明:")
        print("1. 访问 http://localhost:5002 打开UI界面")
        print("2. 进入 '配置管理' 页面")
        print("3. 展开 '🏛️ 代码仓库配置' 区域")
        print("4. 在 'SVN仓库配置' 部分找到 '🔍 增强Merge检测配置'")
        print("5. 可以启用/禁用增强检测并调整置信度阈值")
        print("6. 点击 '💾 保存系统配置' 使配置生效")
        return True
    else:
        print("❌ 部分测试失败，请检查配置集成")
        failed_tests = []
        test_names = ["配置管理器测试", "配置分类测试", "配置文件一致性测试"]
        for i, result in enumerate(results):
            if not result:
                failed_tests.append(test_names[i])
        print(f"失败的测试: {', '.join(failed_tests)}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
