#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对 biz/svn/svn_handler.py 中 diff 解析逻辑的单元测试。

覆盖之前发现的几个会导致"AI 审查出错误问题"的解析缺陷：
1. 编码回退逻辑（GBK/CP936 内容不应被替换为 �）
2. 新增/删除文件的 action 判断（SVN 用 (nonexistent)/(revision 0)，不是 git 的 /dev/null）
3. Property changes 属性变更块应被剥离，不能当成代码 diff 送审
4. 按 "Index: " 切分 diff 时，必须同时锚定紧随其后的 "===" 分隔线，避免误切
5. get_commit_diff_batch 应正确传递扩大后的 diff 上下文行数参数（-x "-U{N}"）

这些测试只做纯字符串解析，不依赖真实 SVN 环境：通过 SVNHandler.__new__(SVNHandler)
跳过 __init__ 里真实的 svn checkout 逻辑。
"""
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from biz.svn.svn_handler import SVNHandler


# ============================================================
# 测试用 svn diff 输出样例（必须顶格书写，保证 "Index: " 出现在真正的行首）
# ============================================================

FIXTURE_MODIFIED = """Index: src/foo.py
===================================================================
--- src/foo.py	(revision 100)
+++ src/foo.py	(revision 101)
@@ -1,3 +1,4 @@
 def foo():
-    return 1
+    return 2
+    # extra line
"""

FIXTURE_ADDED = """Index: src/new_file.py
===================================================================
--- src/new_file.py	(nonexistent)
+++ src/new_file.py	(revision 101)
@@ -0,0 +1,3 @@
+def new_func():
+    pass
+
"""

FIXTURE_DELETED = """Index: src/old_file.py
===================================================================
--- src/old_file.py	(revision 100)
+++ src/old_file.py	(nonexistent)
@@ -1,3 +0,0 @@
-def old_func():
-    pass
-
"""

# 纯属性变更（无任何代码内容变化），只有 svn:eol-style 属性被添加
FIXTURE_PROPERTY_ONLY = """Index: src/settings.py
===================================================================
--- src/settings.py	(revision 100)
+++ src/settings.py	(revision 100)

Property changes on: src/settings.py
___________________________________________________________________
Added: svn:eol-style
## -0,0 +1 ##
+native
\\ No newline at end of property
"""

# 真实代码改动 + 附带的属性变更块混在一起
FIXTURE_MIXED = """Index: src/bar.py
===================================================================
--- src/bar.py	(revision 100)
+++ src/bar.py	(revision 101)
@@ -1,2 +1,3 @@
 def bar():
-    return 1
+    return 2
+    return 3

Property changes on: src/bar.py
___________________________________________________________________
Added: svn:eol-style
## -0,0 +1 ##
+native
\\ No newline at end of property
"""

# 不受支持的文件类型（.exe 不在 SUPPORTED_EXTENSIONS 中）
FIXTURE_UNSUPPORTED_EXT = """Index: bin/tool.exe
===================================================================
--- bin/tool.exe	(revision 100)
+++ bin/tool.exe	(revision 101)
@@ -1,1 +1,1 @@
-old marker
+new marker
"""

# 用于构造"file1 内容中途混入一行形似文件头、但没有紧跟 === 分隔线"的场景
FIXTURE_FOO_PART1 = """Index: src/foo.py
===================================================================
--- src/foo.py	(revision 100)
+++ src/foo.py	(revision 101)
@@ -1,3 +1,4 @@
 def foo():
-    return 1
"""

FIXTURE_FOO_PART2_WITH_STRAY_INDEX_LINE = """Index: not-a-real-file-header
+    return 2
+    # extra line
"""


class TestParseDiffOutput(TestCase):
    """测试 SVNHandler._parse_diff_output 纯解析逻辑"""

    def setUp(self):
        # 跳过 __init__（避免真实 svn checkout），仅测试无状态的解析方法
        self.handler = SVNHandler.__new__(SVNHandler)

    def test_modified_file_reports_action_m_with_correct_counts(self):
        changes = self.handler._parse_diff_output(FIXTURE_MODIFIED)

        self.assertEqual(len(changes), 1)
        change = changes[0]
        self.assertEqual(change['new_path'], 'src/foo.py')
        self.assertEqual(change['action'], 'M')
        self.assertEqual(change['additions'], 2)
        self.assertEqual(change['deletions'], 1)

    def test_added_file_reports_action_a(self):
        changes = self.handler._parse_diff_output(FIXTURE_ADDED)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['new_path'], 'src/new_file.py')
        self.assertEqual(changes[0]['action'], 'A')

    def test_deleted_file_excluded_by_default(self):
        changes = self.handler._parse_diff_output(FIXTURE_DELETED, include_deleted=False)

        self.assertEqual(changes, [])

    def test_deleted_file_included_when_requested(self):
        changes = self.handler._parse_diff_output(FIXTURE_DELETED, include_deleted=True)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['new_path'], 'src/old_file.py')
        self.assertEqual(changes[0]['action'], 'D')

    def test_property_only_change_is_completely_skipped(self):
        """纯属性变更（没有 @@ 内容 hunk）不应作为代码变更送审"""
        changes = self.handler._parse_diff_output(FIXTURE_PROPERTY_ONLY)

        self.assertEqual(changes, [])

    def test_mixed_content_and_property_change_strips_property_section(self):
        """代码改动和属性变更同时存在时，属性变更段落必须被剥离"""
        changes = self.handler._parse_diff_output(FIXTURE_MIXED)

        self.assertEqual(len(changes), 1)
        change = changes[0]
        self.assertEqual(change['new_path'], 'src/bar.py')
        self.assertEqual(change['action'], 'M')
        # 属性变更段落不应出现在送审的 diff 文本里
        self.assertNotIn('Property changes on', change['diff'])
        self.assertNotIn('+native', change['diff'])
        # additions/deletions 应只反映真实代码行，不包含属性值行
        self.assertEqual(change['additions'], 2)
        self.assertEqual(change['deletions'], 1)

    def test_unsupported_extension_is_filtered_out(self):
        changes = self.handler._parse_diff_output(FIXTURE_UNSUPPORTED_EXT)

        self.assertEqual(changes, [])

    def test_stray_index_like_line_without_separator_does_not_missplit(self):
        """
        文件内容中途出现一行形似 "Index: xxx" 但后面没有紧跟 "===" 分隔线时，
        不应被误判为新文件块的起点，导致真实文件的内容被截断/错误拆分。
        """
        stdout = FIXTURE_FOO_PART1 + FIXTURE_FOO_PART2_WITH_STRAY_INDEX_LINE + FIXTURE_ADDED

        changes = self.handler._parse_diff_output(stdout)

        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0]['new_path'], 'src/foo.py')
        # 混入的那一行应该原样保留在 foo.py 的 diff 内容里，而不是被当成切分点丢掉
        self.assertIn('not-a-real-file-header', changes[0]['diff'])
        self.assertIn('# extra line', changes[0]['diff'])
        self.assertEqual(changes[1]['new_path'], 'src/new_file.py')
        self.assertEqual(changes[1]['action'], 'A')

    def test_multiple_files_in_single_diff_output(self):
        stdout = FIXTURE_MODIFIED + FIXTURE_ADDED + FIXTURE_DELETED
        changes = self.handler._parse_diff_output(stdout, include_deleted=True)

        paths_and_actions = [(c['new_path'], c['action']) for c in changes]
        self.assertEqual(paths_and_actions, [
            ('src/foo.py', 'M'),
            ('src/new_file.py', 'A'),
            ('src/old_file.py', 'D'),
        ])


class TestDetectAction(TestCase):
    """测试 SVNHandler._detect_action 对 SVN 真实标注方式的识别"""

    def setUp(self):
        self.handler = SVNHandler.__new__(SVNHandler)

    def test_nonexistent_old_side_is_added(self):
        diff_content = (
            "--- foo.py\t(nonexistent)\n"
            "+++ foo.py\t(revision 5)\n"
        )
        self.assertEqual(self.handler._detect_action(diff_content), 'A')

    def test_nonexistent_new_side_is_deleted(self):
        diff_content = (
            "--- foo.py\t(revision 5)\n"
            "+++ foo.py\t(nonexistent)\n"
        )
        self.assertEqual(self.handler._detect_action(diff_content), 'D')

    def test_revision_zero_old_side_is_added(self):
        diff_content = (
            "--- foo.py\t(revision 0)\n"
            "+++ foo.py\t(revision 5)\n"
        )
        self.assertEqual(self.handler._detect_action(diff_content), 'A')

    def test_both_sides_exist_is_modified(self):
        diff_content = (
            "--- foo.py\t(revision 5)\n"
            "+++ foo.py\t(revision 6)\n"
        )
        self.assertEqual(self.handler._detect_action(diff_content), 'M')

    def test_git_style_dev_null_still_supported_as_fallback(self):
        diff_content = (
            "--- /dev/null\n"
            "+++ foo.py\n"
        )
        self.assertEqual(self.handler._detect_action(diff_content), 'A')


class TestSafeDecode(TestCase):
    """测试 _safe_decode 对非 UTF-8（如 GBK）内容的正确解码"""

    def setUp(self):
        self.handler = SVNHandler.__new__(SVNHandler)

    def test_gbk_bytes_are_decoded_correctly_not_replaced(self):
        text = "修复空指针异常，涉及中文注释"
        gbk_bytes = text.encode('gbk')

        decoded = self.handler._safe_decode(gbk_bytes)

        self.assertEqual(decoded, text)
        self.assertNotIn('\ufffd', decoded)  # 不应包含替换字符 �

    def test_utf8_bytes_are_decoded_correctly(self):
        text = "修复空指针异常"
        decoded = self.handler._safe_decode(text.encode('utf-8'))
        self.assertEqual(decoded, text)

    def test_empty_bytes_returns_empty_string(self):
        self.assertEqual(self.handler._safe_decode(b''), "")


class TestRunSvnCommandEncoding(TestCase):
    """
    测试 _run_svn_command 端到端解码行为：
    验证修复后的实现不再使用 text=True + errors='replace'（该组合会让解码错误被
    静默吞掉、无法真正回退到 gbk/cp936），而是统一以二进制模式读取后交给
    _safe_decode 做严格的多编码尝试。
    """

    def setUp(self):
        self.handler = SVNHandler.__new__(SVNHandler)
        self.handler.svn_username = None
        self.handler.svn_password = None

    @patch('biz.svn.svn_handler.subprocess.run')
    def test_gbk_stdout_is_decoded_without_corruption(self, mock_run):
        text = "提交信息包含中文：修复空指针异常"
        mock_result = MagicMock()
        mock_result.stdout = text.encode('gbk')
        mock_result.stderr = b''
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        stdout, stderr, returncode = self.handler._run_svn_command(['svn', 'log'])

        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, text)
        self.assertNotIn('\ufffd', stdout)

        # 确认底层调用使用的是二进制模式，而不是 text=True + errors='replace'
        _, kwargs = mock_run.call_args
        self.assertFalse(kwargs.get('text', False))


class TestGetCommitDiffBatch(TestCase):
    """测试 get_commit_diff_batch 对外行为：命令构造 + 解析委托 + 错误处理"""

    def setUp(self):
        self.handler = SVNHandler.__new__(SVNHandler)
        self.handler.svn_username = None
        self.handler.svn_password = None
        self.handler.svn_local_path = '/tmp/fake_svn_wc'

    @patch.object(SVNHandler, '_run_svn_command')
    def test_command_includes_wider_diff_context_and_delegates_parsing(self, mock_run):
        mock_run.return_value = (FIXTURE_MODIFIED, '', 0)

        changes = self.handler.get_commit_diff_batch({'revision': '123'})

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['new_path'], 'src/foo.py')

        called_command = mock_run.call_args[0][0]
        self.assertIn('-x', called_command)
        context_arg = called_command[called_command.index('-x') + 1]
        self.assertRegex(context_arg, r'^-U\d+$')

    @patch.object(SVNHandler, '_run_svn_command')
    def test_raises_runtime_error_when_svn_command_fails(self, mock_run):
        mock_run.return_value = ('', 'svn: E200030: sqlite busy', 1)

        with self.assertRaises(RuntimeError):
            self.handler.get_commit_diff_batch({'revision': '123'})

    @patch.object(SVNHandler, '_run_svn_command')
    def test_empty_diff_returns_empty_list(self, mock_run):
        mock_run.return_value = ('   ', '', 0)

        changes = self.handler.get_commit_diff_batch({'revision': '123'})

        self.assertEqual(changes, [])


if __name__ == '__main__':
    main()
