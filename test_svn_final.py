#!/usr/bin/env python3
"""
SVN版本追踪测试脚本（最终版）
"""
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import sqlite3
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biz.svn.svn_handler import SVNHandler
from biz.svn.svn_worker import process_svn_commit
from biz.utils.version_tracker import VersionTracker


def test_svn_version_tracking():
    """测试SVN版本追踪和去重功能"""
    print("\n开始测试SVN版本追踪和去重功能...")
    
    # 创建临时目录和数据库
    temp_dir = tempfile.mkdtemp()
    svn_dir = os.path.join(temp_dir, '.svn')
    os.makedirs(svn_dir)
    
    # 创建临时SQLite数据库用于测试
    test_db_path = os.path.join(temp_dir, 'test_versions.db')
    
    try:
        # 保存原始数据库路径并使用新的测试数据库
        original_db_file = VersionTracker.DB_FILE
        VersionTracker.DB_FILE = test_db_path
        VersionTracker.init_db()
        
        # 创建SVN处理器
        handler = SVNHandler("http://test.svn.repo", temp_dir)
          # 模拟提交数据
        test_commit = {
            'revision': '456',
            'author': 'test_dev',
            'date': '2023-12-20T15:30:00.000000Z',
            'message': '修复重要Bug',
            'paths': [
                {'action': 'M', 'path': '/trunk/src/main.py'},
                {'action': 'A', 'path': '/trunk/src/utils.py'}
            ]
        }
        
        # 设置环境变量启用版本追踪
        os.environ['VERSION_TRACKING_ENABLED'] = '1'
        os.environ['SVN_REVIEW_ENABLED'] = '1'
        
        print(f"环境变量设置:")
        print(f"- VERSION_TRACKING_ENABLED: {os.environ.get('VERSION_TRACKING_ENABLED')}")
        print(f"- SVN_REVIEW_ENABLED: {os.environ.get('SVN_REVIEW_ENABLED')}")
        
        # 检查版本追踪数据库初始状态
        print("检查版本追踪数据库初始状态...")
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM version_tracker")
        initial_count = cursor.fetchone()[0]
        conn.close()
        print(f"初始数据库记录数: {initial_count}")
        
        # 模拟代码审查相关依赖，但允许真实的版本追踪操作
        with patch('biz.svn.svn_worker.CodeReviewer') as mock_reviewer_class, \
             patch('biz.svn.svn_worker.notifier') as mock_notifier, \
             patch('biz.svn.svn_worker.event_manager') as mock_event, \
             patch('biz.svn.svn_worker.filter_svn_changes') as mock_filter, \
             patch.object(handler, 'get_commit_changes') as mock_get_changes:
            
            # 创建模拟的ReviewCode实例
            mock_reviewer = MagicMock()
            mock_reviewer_class.return_value = mock_reviewer
            
            # 模拟代码审查结果
            mock_reviewer.review_and_strip_code.return_value = "修复代码逻辑正确，符合规范。评分: 85分"
            mock_reviewer_class.parse_review_score.return_value = 85
            
            # 模拟get_commit_changes返回
            mock_changes = [
                {
                    'new_path': '/trunk/src/main.py',
                    'old_path': '/trunk/src/main.py',
                    'action': 'M',
                    'diff': """--- a/main.py
+++ b/main.py
@@ -1,3 +1,5 @@
 def main():
+    print("新增代码行1")
+    print("新增代码行2")
     pass""",
                    'additions': 2,
                    'deletions': 0
                }
            ]
            mock_get_changes.return_value = mock_changes
            
            # 模拟filter_svn_changes返回相同的变更（通过过滤）
            mock_filter.return_value = mock_changes
            
            # 第一次调用process_svn_commit，应该进行审查
            print("第一次处理SVN提交...")
            print(f"模拟的变更: {mock_changes}")
            process_svn_commit(handler, test_commit, temp_dir, "test_repo")
            
            print(f"第一次处理后统计:")
            print(f"- get_commit_changes被调用: {mock_get_changes.called}")
            print(f"- filter_svn_changes被调用: {mock_filter.called}")
            print(f"- review_and_strip_code被调用: {mock_reviewer.review_and_strip_code.called}")
            
            # 验证代码审查被调用了
            assert mock_reviewer.review_and_strip_code.called, "第一次审查应该被调用"
            
            # 验证数据库中有记录
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM version_tracker WHERE project_name='test_repo'")
            count = cursor.fetchone()[0]
            conn.close()
            
            assert count == 1, f"数据库中应该有1条记录，实际有{count}条"
            print("✓ 第一次审查完成，版本已记录")
            
            # 重置mock以便测试第二次调用
            mock_reviewer.reset_mock()
            
            # 第二次调用process_svn_commit，应该跳过审查（去重）
            print("第二次处理相同SVN提交...")
            process_svn_commit(handler, test_commit, temp_dir, "test_repo")
            
            # 验证代码审查没有被再次调用
            assert not mock_reviewer.review_and_strip_code.called, "第二次审查应该被跳过（去重）"
            
            print("✓ SVN版本去重功能正常工作")
            
            # 验证数据库中仍然只有一条记录
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM version_tracker WHERE project_name='test_repo'")
            count = cursor.fetchone()[0]
            conn.close()
            
            assert count == 1, f"数据库中应该仍然只有1条记录，实际有{count}条"
            print("✓ 版本追踪数据库记录正确")
            
            # 测试不同revision的处理
            test_commit_2 = test_commit.copy()
            test_commit_2['revision'] = '457'
            test_commit_2['message'] = '新功能开发'
            
            print("处理不同revision的SVN提交...")
            process_svn_commit(handler, test_commit_2, temp_dir, "test_repo")
            
            # 验证新revision会被审查
            assert mock_reviewer.review_and_strip_code.called, "不同revision应该被审查"
            print("✓ 不同revision正常进行审查")
            
            # 验证数据库中现在有两条记录
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM version_tracker WHERE project_name='test_repo'")
            count = cursor.fetchone()[0]
            conn.close()
            
            assert count == 2, f"数据库中应该有2条记录，实际有{count}条"
            print("✓ 不同revision也被正确记录")
        
        print("✓ SVN版本追踪和去重功能测试通过")
        
    except Exception as e:
        print(f"❌ SVN版本追踪测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # 恢复原始数据库路径
        VersionTracker.DB_FILE = original_db_file
        
        # 清理环境变量
        if 'VERSION_TRACKING_ENABLED' in os.environ:
            del os.environ['VERSION_TRACKING_ENABLED']
        if 'SVN_REVIEW_ENABLED' in os.environ:
            del os.environ['SVN_REVIEW_ENABLED']
        
        # 清理临时目录
        shutil.rmtree(temp_dir)


def main():
    """运行测试"""
    print("=== SVN版本追踪功能测试开始 ===")
    
    try:
        test_svn_version_tracking()
        
        print("\n=== 所有测试通过！ ===")
        print("SVN版本追踪和去重功能已准备就绪，可以正常使用。")
        print("✓ 相同SVN revision不会被重复审查")
        print("✓ 不同SVN revision会正常进行审查")
        print("✓ 版本追踪数据库记录正确")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
