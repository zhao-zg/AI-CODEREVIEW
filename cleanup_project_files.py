#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目文件清理工具
识别并删除多余的临时文件、测试文件和过期的报告文件
"""

import os
import json
from pathlib import Path
from datetime import datetime

def analyze_project_files():
    """分析项目文件，识别可删除的文件"""
    project_root = Path(".")
    
    # 定义文件分类
    categories = {
        "临时测试文件": [],
        "过期报告文件": [],  
        "诊断工具文件": [],
        "JSON报告数据": [],
        "日志文件": [],
        "重复/无用脚本": [],
        "保留文件": []
    }
    
    # 文件分类规则
    temp_test_patterns = [
        "test_*.py",
        "check_*.py", 
        "debug_*.py",
        "verify_*.py",
        "diagnose_*.py"
    ]
    
    report_patterns = [
        "*_report.md",
        "*_fix_report.md", 
        "*_summary.md",
        "*_REPORT.md"
    ]
    
    json_data_patterns = [
        "*.json"
    ]
    
    log_patterns = [
        "*.log"
    ]
    
    obsolete_scripts = [
        "fix_*.bat",
        "test_*.sh"
    ]
    
    # 扫描文件
    for file_path in project_root.iterdir():
        if file_path.is_file():
            file_name = file_path.name
            
            # 检查是否匹配临时测试文件
            if any(file_path.match(pattern) for pattern in temp_test_patterns):
                categories["临时测试文件"].append(file_name)
            
            # 检查是否匹配报告文件
            elif any(file_path.match(pattern) for pattern in report_patterns):
                categories["过期报告文件"].append(file_name)
            
            # 检查JSON数据文件
            elif any(file_path.match(pattern) for pattern in json_data_patterns):
                categories["JSON报告数据"].append(file_name)
            
            # 检查日志文件
            elif any(file_path.match(pattern) for pattern in log_patterns):
                categories["日志文件"].append(file_name)
            
            # 检查过期脚本
            elif any(file_path.match(pattern) for pattern in obsolete_scripts):
                categories["重复/无用脚本"].append(file_name)
            
            # 诊断工具（单独处理）
            elif "timeout_realtime_diagnosis" in file_name or "jedi_api" in file_name:
                categories["诊断工具文件"].append(file_name)
            
            # 其他重要文件保留
            else:
                categories["保留文件"].append(file_name)
    
    return categories

def generate_cleanup_plan(categories):
    """生成清理计划"""
    cleanup_plan = {
        "建议删除": {},
        "建议保留": {},
        "需要确认": {}
    }
    
    # 建议删除的文件类型
    cleanup_plan["建议删除"]["临时测试文件"] = categories["临时测试文件"]
    cleanup_plan["建议删除"]["过期报告文件"] = categories["过期报告文件"] 
    cleanup_plan["建议删除"]["JSON报告数据"] = categories["JSON报告数据"]
    cleanup_plan["建议删除"]["日志文件"] = [f for f in categories["日志文件"] if f != "app.log"]
    cleanup_plan["建议删除"]["重复/无用脚本"] = categories["重复/无用脚本"]
    
    # 需要确认的文件
    cleanup_plan["需要确认"]["诊断工具文件"] = categories["诊断工具文件"]
    
    # 建议保留的核心文件
    core_files = [
        "api.py", "ui.py", "requirements.txt", "README.md", 
        "CHANGELOG.md", "LICENSE", "Dockerfile", "docker-compose.yml",
        "run_ui.bat", "run_ui.sh", "start.sh", "start_windows.bat"
    ]
    cleanup_plan["建议保留"]["核心文件"] = [f for f in categories["保留文件"] if f in core_files]
    cleanup_plan["建议保留"]["其他保留文件"] = [f for f in categories["保留文件"] if f not in core_files]
    
    return cleanup_plan

def execute_cleanup(cleanup_plan, confirm=True):
    """执行清理操作"""
    total_deleted = 0
    deleted_files = []
    
    print("🧹 开始执行文件清理...")
    print("=" * 60)
    
    for category, files in cleanup_plan["建议删除"].items():
        if not files:
            continue
            
        print(f"\n📁 {category} ({len(files)} 个文件):")
        
        for file_name in files:
            file_path = Path(file_name)
            if file_path.exists():
                try:
                    if confirm:
                        response = input(f"  删除 {file_name}? (y/N): ").strip().lower()
                        if response not in ['y', 'yes']:
                            print(f"  ⏭️  跳过: {file_name}")
                            continue
                    
                    file_path.unlink()
                    deleted_files.append(file_name)
                    total_deleted += 1
                    print(f"  ✅ 已删除: {file_name}")
                    
                except Exception as e:
                    print(f"  ❌ 删除失败 {file_name}: {e}")
            else:
                print(f"  ⚠️  文件不存在: {file_name}")
    
    return total_deleted, deleted_files

def main():
    """主函数"""
    print("🔍 AI-CodeReview 项目文件清理工具")
    print("=" * 60)
    
    # 分析文件
    print("📊 正在分析项目文件...")
    categories = analyze_project_files()
    
    # 生成清理计划
    cleanup_plan = generate_cleanup_plan(categories)
    
    # 显示分析结果
    print(f"\n📋 文件分析结果:")
    print("-" * 40)
    
    total_files = 0
    for category, files in categories.items():
        count = len(files)
        total_files += count
        print(f"{category}: {count} 个文件")
    
    print(f"\n总文件数: {total_files}")
    
    # 显示清理计划
    print(f"\n🎯 清理计划:")
    print("-" * 40)
    
    total_to_delete = 0
    for category, files in cleanup_plan["建议删除"].items():
        count = len(files)
        total_to_delete += count
        if count > 0:
            print(f"建议删除 - {category}: {count} 个文件")
            for file_name in files[:5]:  # 只显示前5个
                print(f"  • {file_name}")
            if count > 5:
                print(f"  • ... 还有 {count-5} 个文件")
    
    if cleanup_plan["需要确认"]["诊断工具文件"]:
        print(f"\n🤔 需要确认 - 诊断工具文件: {len(cleanup_plan['需要确认']['诊断工具文件'])} 个")
        for file_name in cleanup_plan["需要确认"]["诊断工具文件"]:
            print(f"  • {file_name}")
    
    print(f"\n📈 预计可清理: {total_to_delete} 个文件")
    
    # 确认执行
    if total_to_delete > 0:
        print(f"\n⚠️  即将删除 {total_to_delete} 个文件")
        response = input("确认执行清理? (y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            total_deleted, deleted_files = execute_cleanup(cleanup_plan, confirm=False)
            
            print(f"\n✅ 清理完成!")
            print(f"实际删除: {total_deleted} 个文件")
            
            # 保存清理记录
            cleanup_record = {
                "timestamp": datetime.now().isoformat(),
                "total_deleted": total_deleted,
                "deleted_files": deleted_files,
                "cleanup_plan": cleanup_plan
            }
            
            with open("cleanup_record.json", "w", encoding="utf-8") as f:
                json.dump(cleanup_record, f, indent=2, ensure_ascii=False)
            
            print(f"📋 清理记录已保存到: cleanup_record.json")
        else:
            print("❌ 取消清理操作")
    else:
        print("✨ 没有需要清理的文件")
    
    print(f"\n🎉 清理工具执行完成!")

if __name__ == "__main__":
    main()
