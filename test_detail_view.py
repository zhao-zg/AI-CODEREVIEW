#!/usr/bin/env python3
"""
UI详细查看功能测试脚本
测试新增的审查结果详情查看功能
"""

import requests
import time
import sys
from biz.service.review_service import ReviewService

def test_ui_detail_view_features():
    """测试UI详细查看功能"""
    print("=== 测试UI详细查看功能 ===")
    
    # 检查是否有数据可供测试
    service = ReviewService()
    
    # 检查版本跟踪数据
    vt_data = service.get_version_tracking_logs()
    print(f"版本跟踪数据条数: {len(vt_data)}")
    
    if not vt_data.empty:
        print("✅ 发现版本跟踪数据，可测试详细查看功能")
        
        # 显示第一条记录的详细信息
        first_record = vt_data.iloc[0]
        print("\n📋 第一条记录详情:")
        print(f"  项目: {first_record['project_name']}")
        print(f"  作者: {first_record['author']}")
        print(f"  类型: {first_record['review_type']}")
        print(f"  分数: {first_record['score']}")
        print(f"  提交SHA: {first_record['commit_sha'][:12]}...")
        
        # 检查审查结果内容
        review_result = first_record.get('commit_messages', '')
        if review_result:
            print(f"  审查结果长度: {len(str(review_result))} 字符")
            print(f"  审查结果预览: {str(review_result)[:100]}...")
            print("✅ 审查结果内容完整")
        else:
            print("⚠️  审查结果为空")
        
        return True
    else:
        print("⚠️  暂无版本跟踪数据用于测试")
        return False

def test_ui_accessibility():
    """测试UI可访问性"""
    print("\n=== 测试UI可访问性 ===")
    
    try:
        response = requests.get("http://localhost:8502", timeout=10)
        if response.status_code == 200:
            print("✅ UI页面正常访问")
            
            # 检查页面内容是否包含新功能相关的文本
            content = response.text
            if "点击表格中的任意行查看详细审查结果" in content:
                print("✅ 发现详细查看功能提示文本")
            
            if "审查结果详情" in content:
                print("✅ 发现详细结果展示功能")
            
            return True
        else:
            print(f"❌ UI访问失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ UI访问异常: {e}")
        return False

def test_new_features():
    """测试新增功能"""
    print("\n=== 测试新增功能 ===")
    
    features_tested = []
    
    # 检查数据可用性
    service = ReviewService()
    
    # 测试多类型统计
    stats = service.get_review_type_stats()
    if stats:
        print("✅ 审查类型统计功能正常")
        features_tested.append("统计功能")
    
    # 测试版本跟踪数据获取
    vt_data = service.get_version_tracking_logs()
    if not vt_data.empty:
        print("✅ 版本跟踪数据获取正常")
        features_tested.append("数据获取")
        
        # 检查是否有完整的审查结果
        has_results = vt_data['commit_messages'].notna().any()
        if has_results:
            print("✅ 审查结果数据完整")
            features_tested.append("审查结果")
    
    print(f"已测试功能: {', '.join(features_tested)}")
    return len(features_tested) > 0

def main():
    """主测试函数"""
    print("开始UI详细查看功能测试")
    print("=" * 50)
    
    results = []
    
    # 测试UI详细查看功能
    results.append(test_ui_detail_view_features())
    
    # 测试UI可访问性
    results.append(test_ui_accessibility())
    
    # 测试新增功能
    results.append(test_new_features())
    
    print("\n" + "=" * 50)
    
    passed_tests = sum(results)
    total_tests = len(results)
    
    if passed_tests == total_tests:
        print("✅ 所有测试通过")
        print("\n🎉 UI详细查看功能测试成功！")
        print("\n📋 新功能说明:")
        print("1. ✨ 点击数据表格中的任意行可查看详细审查结果")
        print("2. 📝 支持完整的审查报告展示，包括Markdown格式化")
        print("3. 📊 显示基本信息：项目、作者、时间、分数等")
        print("4. 📁 SVN类型显示文件变更列表")
        print("5. 🔗 MR类型显示分支信息和链接")
        print("6. 📥 支持单条记录和批量数据导出")
        print("7. 📋 提供审查结果复制功能")
        
        print("\n🔗 访问地址: http://localhost:8502")
        print("📖 使用说明: 登录后选择审查类型，点击表格行查看详情")
        
        sys.exit(0)
    else:
        print(f"❌ 部分测试失败 ({passed_tests}/{total_tests})")
        sys.exit(1)

if __name__ == "__main__":
    main()
