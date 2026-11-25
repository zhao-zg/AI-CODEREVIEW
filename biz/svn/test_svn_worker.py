#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对 biz/svn/svn_worker.py 中定时增量检查（handle_svn_changes）检查点推进逻辑的单元测试。

覆盖"一次定时检查周期内有多次提交时丢提交"的几个场景：
1. 游标按 revision 推进（查询 游标+1 ~ HEAD），而不是按"检查结束时间"推进
2. 提交数达到 check_limit 被截断时，游标只推进到已取回的最大 revision，剩余提交下次继续
3. svn log / HEAD 查询失败时不推进检查点，不能当成"没有提交"

不依赖真实 SVN 环境：SVNHandler 用 MagicMock 替代，检查点数据库指向临时文件。
"""
import os
import shutil
import tempfile
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from biz.svn import svn_worker
from biz.utils.svn_checkpoint import SVNCheckpointManager

REPO = 'test-repo'


def _commits(*revisions):
    return [{'revision': str(r), 'author': 'dev', 'date': '', 'message': f'r{r}', 'paths': []} for r in revisions]


class TestScheduledIncrementalCheck(TestCase):
    def setUp(self):
        tmp_dir = tempfile.mkdtemp(prefix='svn_ckpt_test_')
        self.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)
        db_patch = patch.object(SVNCheckpointManager, 'DB_FILE', os.path.join(tmp_dir, 'data.db'))
        db_patch.start()
        self.addCleanup(db_patch.stop)
        SVNCheckpointManager.init_db()
        svn_worker._processed_revisions_cache.clear()

        self.handler = MagicMock()
        self.handler.update_working_copy.return_value = True
        handler_patch = patch.object(svn_worker, 'SVNHandler', return_value=self.handler)
        handler_patch.start()
        self.addCleanup(handler_patch.stop)

        process_patch = patch.object(svn_worker, 'process_svn_commit')
        self.process = process_patch.start()
        self.addCleanup(process_patch.stop)

    def _check(self, limit=100):
        svn_worker.handle_svn_changes('svn://host/repo/trunk', 'wc', check_limit=limit,
                                      repo_name=REPO, trigger_type='scheduled')

    def _processed(self):
        return [c.args[1]['revision'] for c in self.process.call_args_list]

    def test_queries_from_cursor_to_head_and_advances_to_head(self):
        SVNCheckpointManager.update_checkpoint(REPO, '100')
        self.handler.get_head_revision.return_value = 105
        self.handler.get_commits_by_range.return_value = _commits(101, 103, 105)

        self._check()

        self.handler.get_commits_by_range.assert_called_once_with('101:105', 100)
        self.assertEqual(self._processed(), ['101', '103', '105'])
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 105)

    def test_no_new_revision_skips_log_query(self):
        SVNCheckpointManager.update_checkpoint(REPO, '100')
        self.handler.get_head_revision.return_value = 100

        self._check()

        self.handler.get_commits_by_range.assert_not_called()
        self.process.assert_not_called()
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 100)

    def test_truncated_by_limit_leaves_rest_for_next_check(self):
        SVNCheckpointManager.update_checkpoint(REPO, '100')
        self.handler.get_head_revision.return_value = 105
        self.handler.get_commits_by_range.side_effect = [_commits(101, 102), _commits(103, 104), _commits(105)]

        self._check(limit=2)
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 102)
        self._check(limit=2)
        self._check(limit=2)

        self.assertEqual([c.args[0] for c in self.handler.get_commits_by_range.call_args_list],
                         ['101:105', '103:105', '105:105'])
        self.assertEqual(self._processed(), ['101', '102', '103', '104', '105'])
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 105)

    def test_query_failure_does_not_advance_checkpoint(self):
        SVNCheckpointManager.update_checkpoint(REPO, '100')

        self.handler.get_head_revision.return_value = 105
        self.handler.get_commits_by_range.return_value = None
        self._check()
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 100)

        self.handler.get_head_revision.return_value = None
        self._check()
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 100)

        self.process.assert_not_called()

    def test_without_revision_cursor_falls_back_to_time_then_uses_cursor(self):
        # 旧版本遗留的检查点：只有检查时间，没有 revision 游标
        SVNCheckpointManager.update_checkpoint(REPO)
        self.handler.get_head_revision.return_value = 50
        self.handler.get_commits_by_range.return_value = _commits(49, 50)

        self._check()

        range_arg = self.handler.get_commits_by_range.call_args.args[0]
        self.assertRegex(range_arg, r'^\{\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\}:50$')
        self.assertEqual(self._processed(), ['49', '50'])
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 50)

    def test_cursor_beyond_head_is_reset(self):
        # 同名仓库被换成另一个 revision 更小的仓库：旧游标失效，不能永远判定为"没有新提交"
        SVNCheckpointManager.update_checkpoint(REPO, '9000')
        self.handler.get_head_revision.return_value = 20
        self.handler.get_commits_by_range.return_value = _commits(20)

        self._check()

        self.assertEqual(self._processed(), ['20'])
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 20)

    def test_checkpoint_does_not_move_backwards(self):
        # 并发检查任务中先开始、后结束的那个不应把游标写回旧值
        SVNCheckpointManager.update_checkpoint(REPO, '108')
        SVNCheckpointManager.update_checkpoint(REPO, '105')
        self.assertEqual(SVNCheckpointManager.get_last_revision(REPO), 108)


if __name__ == '__main__':
    main()
