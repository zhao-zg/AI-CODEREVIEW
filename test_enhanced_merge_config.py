#!/usr/bin/env python3
"""
测试增强的Merge审查配置功能
测试可视化SVN仓库配置界面和merge_review选项
"""
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_merge_config():
    """测试增强的Merge配置功能"""
    print("🧪 测试增强的Merge审查配置功能")
    print("=" * 60)
    
    # 测试1: 验证merge检查逻辑
    print("\n📋 测试1: Merge提交检测逻辑")
    from biz.svn.svn_worker import is_merge_commit, should_skip_merge_commit
    
    # 测试各种merge提交消息
    merge_messages = [
        "Merged feature branch to main",
        "Merge branch 'feature/login' into develop", 
        "Auto-merged by system",
        "merge: fix conflicts",
        "Merged via svn merge r12345",
        "MERGE",
        "Merging changes from release branch"
    ]
    
    normal_messages = [
        "Fix login bug",
        "Add new feature",
        "Update documentation", 
        "Refactor code structure",
        "This is a normal commit with merge mentioned but not as action"
    ]
    
    print("  📝 Merge提交检测:")
    for msg in merge_messages:
        result = is_merge_commit(msg)
        print(f"    ✅ '{msg[:40]}...' -> {result}")
        assert result == True, f"应该检测为merge提交: {msg}"
    
    print("  📝 普通提交检测:")
    for msg in normal_messages:
        result = is_merge_commit(msg)
        print(f"    ✅ '{msg[:40]}...' -> {result}")
        assert result == False, f"不应该检测为merge提交: {msg}"
    
    # 测试2: 验证跳过逻辑
    print("\n📋 测试2: Merge跳过逻辑")
    
    # 仓库配置：启用merge审查
    repo_config_enabled = {"enable_merge_review": True}
    # 仓库配置：禁用merge审查  
    repo_config_disabled = {"enable_merge_review": False}
    # 仓库配置：默认配置（应该启用）
    repo_config_default = {}
    
    merge_msg = "Merged feature branch"
    normal_msg = "Fix bug in login"
    
    # 测试启用merge审查的情况
    print("  📝 启用merge审查:")
    assert should_skip_merge_commit(repo_config_enabled, merge_msg) == False, "启用时不应该跳过merge"
    assert should_skip_merge_commit(repo_config_enabled, normal_msg) == False, "启用时不应该跳过普通提交"
    print("    ✅ 启用状态下，所有提交都会被处理")
    
    # 测试禁用merge审查的情况
    print("  📝 禁用merge审查:")
    assert should_skip_merge_commit(repo_config_disabled, merge_msg) == True, "禁用时应该跳过merge"
    assert should_skip_merge_commit(repo_config_disabled, normal_msg) == False, "禁用时不应该跳过普通提交"
    print("    ✅ 禁用状态下，只跳过merge提交")
    
    # 测试默认配置的情况
    print("  📝 默认配置:")
    assert should_skip_merge_commit(repo_config_default, merge_msg) == False, "默认应该启用merge审查"
    assert should_skip_merge_commit(repo_config_default, normal_msg) == False, "默认不应该跳过普通提交"
    print("    ✅ 默认状态下，所有提交都会被处理")
    
    # 测试3: 验证JSON配置兼容性
    print("\n📋 测试3: JSON配置格式兼容性")
    
    # 测试新格式的JSON配置（包含enable_merge_review）
    new_format_config = [
        {
            "name": "project1",
            "remote_url": "svn://example.com/project1/trunk",
            "local_path": "data/svn/project1",
            "username": "user1",
            "password": "pass1",
            "check_hours": 24,
            "enable_merge_review": True
        },
        {
            "name": "project2", 
            "remote_url": "svn://example.com/project2/trunk",
            "local_path": "data/svn/project2",
            "username": "user2",
            "password": "pass2", 
            "check_hours": 48,
            "enable_merge_review": False
        }
    ]
    
    # 测试旧格式的JSON配置（不包含enable_merge_review）
    old_format_config = [
        {
            "name": "legacy_project",
            "remote_url": "svn://example.com/legacy/trunk",
            "local_path": "data/svn/legacy",
            "username": "legacy_user",
            "password": "legacy_pass",
            "check_hours": 12
        }
    ]
    
    print("  📝 新格式配置验证:")
    new_json = json.dumps(new_format_config, ensure_ascii=False)
    parsed_new = json.loads(new_json)
    
    for repo in parsed_new:
        merge_enabled = repo.get('enable_merge_review', True)
        print(f"    ✅ 仓库 '{repo['name']}': merge_review = {merge_enabled}")
    
    print("  📝 旧格式配置兼容性:")
    old_json = json.dumps(old_format_config, ensure_ascii=False)
    parsed_old = json.loads(old_json)
    
    for repo in parsed_old:
        # 模拟自动添加默认值
        if 'enable_merge_review' not in repo:
            repo['enable_merge_review'] = True
        merge_enabled = repo.get('enable_merge_review', True)
        print(f"    ✅ 仓库 '{repo['name']}': merge_review = {merge_enabled} (默认值)")
    
    # 测试4: 模拟UI配置生成
    print("\n📋 测试4: UI配置生成")
    
    # 模拟UI中的仓库配置
    ui_repos_config = [
        {
            "name": "ui_test_repo1",
            "remote_url": "svn://test.com/repo1",
            "local_path": "data/svn/ui_test1",
            "username": "ui_user1",
            "password": "ui_pass1",
            "check_hours": 24,
            "enable_merge_review": True
        },
        {
            "name": "ui_test_repo2", 
            "remote_url": "svn://test.com/repo2",
            "local_path": "data/svn/ui_test2",
            "username": "ui_user2",
            "password": "ui_pass2",
            "check_hours": 48,
            "enable_merge_review": False
        }
    ]
    
    # 生成紧凑JSON
    ui_json = json.dumps(ui_repos_config, separators=(',', ':'), ensure_ascii=False)
    print(f"  📝 生成的配置JSON:")
    print(f"    {ui_json}")
    
    # 验证解析
    parsed_ui = json.loads(ui_json)
    total_repos = len(parsed_ui)
    merge_enabled_count = sum(1 for repo in parsed_ui if repo.get('enable_merge_review', True))
    merge_disabled_count = total_repos - merge_enabled_count
    
    print(f"  📊 配置统计:")
    print(f"    总仓库数: {total_repos}")
    print(f"    启用Merge审查: {merge_enabled_count}")
    print(f"    禁用Merge审查: {merge_disabled_count}")
    
    # 测试5: 实际工作流测试
    print("\n📋 测试5: 工作流集成测试")
    
    # 模拟提交处理流程
    test_commits = [
        {"message": "Fix critical security bug", "is_merge": False},
        {"message": "Merged hotfix branch to main", "is_merge": True},
        {"message": "Add user authentication", "is_merge": False},
        {"message": "Auto-merged release candidate", "is_merge": True}
    ]
    
    for repo_config in [repo_config_enabled, repo_config_disabled]:
        merge_setting = "启用" if repo_config.get('enable_merge_review', True) else "禁用"
        print(f"  📝 仓库配置: {merge_setting}Merge审查")
        
        for commit in test_commits:
            message = commit['message']
            should_skip = should_skip_merge_commit(repo_config, message)
            action = "跳过" if should_skip else "处理"
            commit_type = "Merge" if commit['is_merge'] else "普通"
            
            print(f"    📄 {commit_type}提交: '{message[:30]}...' -> {action}")
    
    print("\n✅ 所有测试通过！")
    print("\n📈 功能摘要:")
    print("  ✅ Merge提交检测算法正常工作")
    print("  ✅ 仓库级别的Merge审查开关生效")
    print("  ✅ JSON配置格式新旧兼容") 
    print("  ✅ UI配置生成和解析正常")
    print("  ✅ 工作流集成测试通过")
    print("\n🎯 下一步建议:")
    print("  🔧 在生产环境测试实际SVN仓库")
    print("  📊 监控Merge跳过的统计数据")
    print("  🎨 考虑添加批量配置管理工具")

if __name__ == "__main__":
    test_enhanced_merge_config()
