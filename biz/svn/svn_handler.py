import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import re
from urllib.parse import urlparse
from biz.utils.log import logger


class SVNHandler:
    """SVN版本控制处理器"""
    
    def __init__(self, svn_remote_url: str, svn_local_path: str, svn_username: str = None, svn_password: str = None):
        """
        初始化SVN处理器
        :param svn_remote_url: SVN远程仓库URL
        :param svn_local_path: SVN仓库本地路径
        :param svn_username: SVN用户名
        :param svn_password: SVN密码
        """
        self.svn_remote_url = svn_remote_url.rstrip('/')
        self.svn_local_path = svn_local_path
        self.svn_username = svn_username
        self.svn_password = svn_password
        
        self._prepare_working_copy()
        # 获取仓库根URL
        self.svn_repo_root_url = self._get_repo_root_url()

    def _prepare_working_copy(self):
        """
        准备SVN工作副本，如果不存在则签出
        """
        if not os.path.exists(self.svn_local_path):
            logger.info(f"本地路径 {self.svn_local_path} 不存在，创建目录...")
            os.makedirs(self.svn_local_path)

        if not os.path.exists(os.path.join(self.svn_local_path, '.svn')):
            logger.info(f"本地SVN工作副本不存在于 {self.svn_local_path}, 执行 checkout...")
            # 使用 . 作为目标，检出到CWD，增加 --ignore-externals 参数
            command = ['svn', 'checkout', '--ignore-externals', self.svn_remote_url, '.']
            stdout, stderr, returncode = self._run_svn_command(command, cwd=self.svn_local_path)
            if returncode != 0:
                raise RuntimeError(f"SVN checkout 失败: {stderr}")
        else:
            logger.info(f"发现SVN工作副本于: {self.svn_local_path}")

    def _get_repo_root_url(self) -> str:
        """
        获取SVN仓库的根URL
        :return: 仓库根URL
        """
        command = ['svn', 'info', '--show-item', 'repos-root-url']
        stdout, stderr, returncode = self._run_svn_command(command, cwd=self.svn_local_path)
        
        if returncode != 0:
            logger.error(f"获取仓库根URL失败: {stderr}")
            # 如果失败，尝试从远程URL推断
            parsed_url = urlparse(self.svn_remote_url)
            return f"{parsed_url.scheme}://{parsed_url.netloc}/projectx"
        
        repo_root_url = stdout.strip()
        logger.info(f"仓库根URL: {repo_root_url}")
        return repo_root_url
    
    def _run_svn_command(self, command: List[str], cwd: Optional[str] = None) -> Tuple[str, str, int]:
        """
        执行SVN命令
        :param command: SVN命令列表
        :param cwd: 命令执行的当前工作目录
        :return: (stdout, stderr, returncode)
        """
        try:
            # 添加认证参数
            if self.svn_username and self.svn_password:
                command.extend(['--username', self.svn_username, '--password', self.svn_password])
            
            # 添加非交互模式和信任服务器证书
            command.extend(['--non-interactive', '--trust-server-cert-failures=unknown-ca,cn-mismatch,expired,not-yet-valid,other'])
            
            logger.info(f"执行SVN命令: {' '.join(command)} in {cwd or 'default cwd'}")
            
            # 始终以二进制模式执行，再交给 _safe_decode 按多种编码严格尝试解码。
            # 注意：之前的实现用 text=True + errors='replace' 让 subprocess 直接解码，
            # 但 errors='replace' 会让解码器遇到非法字节时静默替换为 '�' 而不是抛出
            # UnicodeDecodeError，导致下面"尝试下一种编码"的回退逻辑永远不会被触发，
            # 一旦实际编码不是 utf-8（例如 GBK/CP936 环境的中文提交信息或源码），
            # 内容会被大量替换为 '�'，进而把乱码送进后续的 AI 审查。
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=False  # 二进制模式，交给 _safe_decode 做严格的多编码尝试
            )
            
            stdout = self._safe_decode(result.stdout)
            stderr = self._safe_decode(result.stderr)
            
            return stdout, stderr, result.returncode
        
        except Exception as e:
            logger.error(f"执行SVN命令失败: {e}")
            return "", str(e), -1
    
    def update_working_copy(self) -> bool:
        """
        更新SVN工作副本
        :return: 更新是否成功
        """
        stdout, stderr, returncode = self._run_svn_command(['svn', 'update', '--ignore-externals'], cwd=self.svn_local_path)
        
        if returncode != 0:
            logger.error(f"SVN更新失败: {stderr}")
            
            # 如果是E155037错误（需要cleanup），尝试执行cleanup
            if "svn cleanup" in stderr or "Previous operation has not finished" in stderr:
                logger.info("检测到SVN工作副本需要清理，正在执行cleanup...")
                cleanup_success = self._cleanup_working_copy()
                
                if cleanup_success:
                    # cleanup或重建成功后重试更新
                    logger.info("SVN cleanup/重建成功，重试更新...")
                    stdout, stderr, returncode = self._run_svn_command(['svn', 'update', '--ignore-externals'], cwd=self.svn_local_path)
                    
                    if returncode != 0:
                        logger.error(f"SVN cleanup/重建后更新仍然失败: {stderr}")
                        return False
                else:
                    logger.error("SVN cleanup和重建都失败，无法更新工作副本")
                    return False
            else:
                return False
        
        logger.info("SVN工作副本更新成功")
        return True
    
    def _cleanup_working_copy(self) -> bool:
        """
        清理SVN工作副本
        :return: 清理是否成功
        """
        try:
            logger.info(f"开始清理SVN工作副本: {self.svn_local_path}")
            
            # 尝试标准cleanup
            stdout, stderr, returncode = self._run_svn_command(['svn', 'cleanup'], cwd=self.svn_local_path)
            
            if returncode == 0:
                logger.info("SVN cleanup成功")
                return True
            
            logger.warning(f"标准SVN cleanup失败: {stderr}")
            
            # 检查是否是工作队列错误
            if 'work queue' in stderr.lower() or 'wc.db' in stderr.lower():
                logger.info("检测到工作队列错误，尝试专门修复...")
                if self._fix_work_queue_error():
                    return True
            
            # 如果标准cleanup失败，尝试强制cleanup（SVN 1.7+）
            logger.info("尝试强制cleanup...")
            stdout, stderr, returncode = self._run_svn_command(
                ['svn', 'cleanup', '--remove-unversioned', '--remove-ignored'], 
                cwd=self.svn_local_path
            )
            
            if returncode == 0:
                logger.info("强制SVN cleanup成功")
                return True
            
            logger.error(f"强制SVN cleanup也失败: {stderr}")
            
            # 最后的手段：删除.svn/wc.db锁文件（仅限紧急情况）
            import os
            lock_file = os.path.join(self.svn_local_path, '.svn', 'wc.db-lock')
            if os.path.exists(lock_file):
                logger.info("尝试删除SVN锁文件...")
                try:
                    os.remove(lock_file)
                    logger.info("SVN锁文件删除成功，重试cleanup...")
                    stdout, stderr, returncode = self._run_svn_command(['svn', 'cleanup'], cwd=self.svn_local_path)
                    if returncode == 0:
                        logger.info("删除锁文件后cleanup成功")
                        return True
                except Exception as e:
                    logger.error(f"删除SVN锁文件失败: {e}")

            # 新增：检测并删除 .svn/write-lock 文件
            write_lock_file = os.path.join(self.svn_local_path, '.svn', 'write-lock')
            if os.path.exists(write_lock_file):
                logger.info("尝试删除SVN write-lock文件...")
                try:
                    os.remove(write_lock_file)
                    logger.info("SVN write-lock文件删除成功，重试cleanup...")
                    stdout, stderr, returncode = self._run_svn_command(['svn', 'cleanup'], cwd=self.svn_local_path)
                    if returncode == 0:
                        logger.info("删除write-lock后cleanup成功")
                        return True
                except Exception as e:
                    logger.error(f"删除SVN write-lock文件失败: {e}")
            
            # 如果所有清理方法都失败，尝试重建工作副本
            logger.error(f"所有SVN cleanup方法都失败，尝试重建工作副本: {self.svn_local_path}")
            return self._rebuild_working_copy()
            
        except Exception as e:
            logger.error(f"SVN cleanup过程中发生异常: {e}")
            return False
    
    def _rebuild_working_copy(self) -> bool:
        """
        重建SVN工作副本（当cleanup失败时的最后手段）
        :return: 重建是否成功
        """
        try:
            logger.info(f"开始重建SVN工作副本: {self.svn_local_path}")
            
            # 创建备份目录名
            import time
            backup_name = f"{self.svn_local_path}_backup_{int(time.time())}"
            
            # 备份现有工作副本
            import shutil
            if os.path.exists(self.svn_local_path):
                logger.info(f"备份现有工作副本到: {backup_name}")
                try:
                    shutil.move(self.svn_local_path, backup_name)
                except Exception as e:
                    logger.warning(f"备份工作副本失败: {e}，尝试删除...")
                    try:
                        shutil.rmtree(self.svn_local_path, ignore_errors=True)
                    except Exception as e2:
                        logger.error(f"删除损坏的工作副本也失败: {e2}")
                        return False
            
            # 重新检出工作副本
            logger.info(f"重新检出SVN仓库: {self.svn_remote_url} -> {self.svn_local_path}")
            
            checkout_cmd = ['svn', 'checkout', self.svn_remote_url, self.svn_local_path]
            stdout, stderr, returncode = self._run_svn_command(checkout_cmd)
            
            if returncode == 0:
                logger.info("SVN工作副本重建成功")
                
                # 如果重建成功，可以删除备份（可选）
                if os.path.exists(backup_name):
                    try:
                        logger.info(f"删除备份目录: {backup_name}")
                        shutil.rmtree(backup_name, ignore_errors=True)
                    except Exception as e:
                        logger.warning(f"删除备份目录失败（可忽略）: {e}")
                
                return True
            else:
                logger.error(f"SVN重新检出失败: {stderr}")
                
                # 如果重建失败，尝试恢复备份
                if os.path.exists(backup_name):
                    try:
                        logger.info("重建失败，尝试恢复备份...")
                        shutil.move(backup_name, self.svn_local_path)
                        logger.info("备份恢复成功")
                    except Exception as e:
                        logger.error(f"恢复备份也失败: {e}")
                
                return False
                
        except Exception as e:
            logger.error(f"重建SVN工作副本过程中发生异常: {e}")
            return False
    
    def get_recent_commits(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        获取最近的提交记录
        :param hours: 最近多少小时的提交
        :param limit: 限制提交数量
        :return: 提交记录列表
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        command = [
            'svn', 'log', self.svn_remote_url,
            '--xml',
            '-r', f'{{{start_time_str}}}:{{{end_time_str}}}',
            '-l', str(limit),
            '-v'
        ]
        
        stdout, stderr, returncode = self._run_svn_command(command, cwd=None)
        
        if returncode != 0:
            logger.error(f"获取SVN日志失败: {stderr}")
            return []
        
        return self._parse_log_xml(stdout)
    
    def _parse_log_xml(self, xml_content: str) -> List[Dict]:
        """
        解析SVN log的XML输出
        :param xml_content: XML内容
        :return: 解析后的提交记录
        """
        commits = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for logentry in root.findall('logentry'):
                revision = logentry.get('revision')
                author = logentry.find('author').text if logentry.find('author') is not None else 'unknown'
                date = logentry.find('date').text if logentry.find('date') is not None else ''
                message = logentry.find('msg').text if logentry.find('msg') is not None else ''
                
                paths = []
                paths_element = logentry.find('paths')
                if paths_element is not None:
                    for path in paths_element.findall('path'):
                        action = path.get('action')
                        file_path = path.text
                        paths.append({
                            'action': action,
                            'path': file_path
                        })
                
                commit_info = {
                    'revision': revision,
                    'author': author,
                    'date': date,
                    'message': message.strip() if message else '',
                    'paths': paths
                }
                
                commits.append(commit_info)
                
        except ET.ParseError as e:
            logger.error(f"解析SVN日志XML失败: {e}")
        
        return commits
    
    def get_file_diff(self, file_path: str, revision1: str, revision2: str) -> str:
        """
        获取文件的差异
        :param file_path: 文件路径 (from repo root)
        :param revision1: 旧版本号
        :param revision2: 新版本号
        :return: 差异内容
        """
        target_url = f"{self.svn_repo_root_url}{file_path}"
        command = [
            'svn', 'diff',
            '-r', f'{revision1}:{revision2}',
            target_url
        ]
        
        stdout, stderr, returncode = self._run_svn_command(command, cwd=None)
        
        if returncode != 0:
            logger.error(f"获取文件差异失败 ({target_url}): {stderr}")
            return ""
        
        return stdout

    def get_commit_diff_batch(self, commit: Dict, include_deleted: bool = False) -> List[Dict]:
        """
        使用 svn diff -c 批量获取提交中所有文件的变更内容，替代逐文件远程获取

        Args:
            commit: 提交信息字典（需包含 revision）
            include_deleted: 是否包含删除的文件，默认 False

        Returns:
            变更列表，每个元素包含 new_path, diff, action, full_path, additions, deletions
        """
        revision = commit['revision']
        logger.info(f'批量获取 SVN diff: r{revision}')

        # 执行 svn diff -c {revision}，在工作副本目录下执行，利用本地缓存的凭证
        # -x "-U{N}" 扩大统一 diff 的上下文行数（svn diff 默认仅 3 行），
        # 上下文太少时 AI 经常因为"看不到全貌"而臆测出并不存在的问题
        from biz.utils.default_config import get_env_int
        context_lines = get_env_int('SVN_DIFF_CONTEXT_LINES', 10)
        command = ['svn', 'diff', '-c', revision, '-x', f'-U{context_lines}']
        stdout, stderr, returncode = self._run_svn_command(command, cwd=self.svn_local_path)

        if returncode != 0:
            error_msg = f"批量获取SVN diff失败 (r{revision}): {stderr}"
            logger.error(error_msg)
            # 抛出异常让上游捕获并发送通知，而非静默返回空列表
            raise RuntimeError(error_msg)

        if not stdout.strip():
            logger.info(f'r{revision} diff 为空')
            return []

        changes = self._parse_diff_output(stdout, include_deleted)
        logger.info(f'r{revision} 批量 diff 解析完成: {len(changes)} 个文件')
        return changes

    def _parse_diff_output(self, stdout: str, include_deleted: bool = False) -> List[Dict]:
        """
        解析 `svn diff` 的原始文本输出为结构化变更列表。
        纯字符串处理，不依赖真实 SVN 环境/工作副本，便于单元测试直接调用。

        :param stdout: svn diff 命令的标准输出（可能包含多个文件的 diff）
        :param include_deleted: 是否包含删除的文件
        :return: 变更列表，每个元素包含 new_path, diff, action, full_path, additions, deletions
        """
        changes = []

        # 定位每个文件块的边界：要求 "Index: 文件名" 后紧跟一行 "===...=" 分隔线，
        # 而不是简单按 "^Index: " 切分——避免某行被增删的代码内容本身以 "Index: " 开头时，
        # 被误判为新文件块的起点，导致不同文件的 diff 被错误拆分/拼接。
        header_pattern = re.compile(r'^Index: (?P<path>.+?)\r?\n(?P<sep>=+)\r?\n', re.MULTILINE)
        matches = list(header_pattern.finditer(stdout))

        for i, m in enumerate(matches):
            file_path = m.group('path').strip()
            if not file_path:
                continue

            block_start = m.end()
            block_end = matches[i + 1].start() if i + 1 < len(matches) else len(stdout)
            diff_content = stdout[block_start:block_end].rstrip('\n')

            # 跳过二进制文件
            if 'Cannot display: file marked as a binary type' in diff_content:
                logger.info(f'跳过二进制文件: {file_path}')
                continue

            # 剥离属性变更段落（"Property changes on: ..."）：svn:eol-style / svn:executable /
            # svn:mime-type 等属性变更会在代码 diff 后追加这段内容，其中的属性值行（如 "+native"）
            # 会被误判为代码内容，需要在做内容判断/计数之前先剥离，避免元数据被当成代码送审。
            prop_marker = re.search(r'\r?\nProperty changes on: ', diff_content)
            if prop_marker:
                diff_content = diff_content[:prop_marker.start()].rstrip('\n')

            # 跳过没有真实代码内容 diff 的块（纯属性变更、或内容完全相同只是路径变化等场景）。
            # 注意：不能用 "是否存在以 +/- 开头的行" 作为辅助判断——unified diff 的
            # "--- file (revision N)" / "+++ file (revision N)" 头部本身就是以 -/+ 开头，
            # 会导致这个判断恒为真、形同虚设。真正代表"存在内容变更"的可靠信号是 "@@" hunk 头，
            # 它必然与真实的 +/- 内容行成对出现。
            has_content_diff = bool(re.search(r'^@@', diff_content, re.MULTILINE))
            if not has_content_diff:
                continue

            action = self._detect_action(diff_content)

            # 删除文件处理
            if action == 'D' and not include_deleted:
                continue

            # 检查文件类型是否受支持
            if not self._is_supported_file(file_path):
                continue

            # 构建完整的 diff 文本（Index 头 + 分隔线，保持和原始 svn diff 输出一致的样式，
            # 让 AI 能正确识别文件路径）
            diff_text = f"Index: {file_path}\n{m.group('sep')}\n" + diff_content

            change = {
                'new_path': file_path,
                'diff': diff_text,
                'action': action,
                'full_path': file_path,
                'additions': self._count_additions(diff_content),
                'deletions': self._count_deletions(diff_content)
            }
            changes.append(change)

        return changes

    def _detect_action(self, diff_content: str) -> str:
        """
        从 diff 内容推断文件的变更类型（A=新增, M=修改, D=删除）。

        注意：SVN 表示"文件在该版本不存在"的写法和 git 不同——不是 `/dev/null`，
        而是类似 `(nonexistent)` / `(revision 0)` 这样的标注。这里以 SVN 的实际写法
        为主，同时保留 `/dev/null` 判断作为兼容分支（以防个别环境产生 git 风格 diff）。
        """
        src_match = re.search(r'^--- .*$', diff_content, re.MULTILINE)
        dst_match = re.search(r'^\+\+\+ .*$', diff_content, re.MULTILINE)
        src_line = src_match.group(0) if src_match else ''
        dst_line = dst_match.group(0) if dst_match else ''

        missing_suffix = re.compile(r'\((nonexistent|revision 0)\)\s*$')

        src_missing = bool(missing_suffix.search(src_line)) or '/dev/null' in src_line
        dst_missing = bool(missing_suffix.search(dst_line)) or '/dev/null' in dst_line

        if src_missing and not dst_missing:
            return 'A'
        elif dst_missing and not src_missing:
            return 'D'
        else:
            return 'M'

    def get_commit_changes(self, commit: Dict, use_batch: bool = True, include_deleted: bool = False) -> List[Dict]:
        """
        获取提交的变更内容
        :param commit: 提交信息
        :param use_batch: 是否使用批量 svn diff -c 方式（默认 True，大幅减少 svn 命令调用次数）
        :param include_deleted: 是否包含删除的文件
        :return: 变更列表
        """
        if use_batch:
            return self.get_commit_diff_batch(commit, include_deleted)

        # 保留旧的逐文件方式作为 fallback
        changes = []
        revision = commit['revision']
        prev_revision = str(int(revision) - 1)

        for path_info in commit['paths']:
            file_path = path_info['path']
            action = path_info['action']

            if action == 'D' or not self._is_supported_file(file_path):
                continue

            diff_content = ""
            if action == 'A':
                diff_content = self._get_file_content(file_path, revision)
            elif action == 'M':
                diff_content = self.get_file_diff(file_path, prev_revision, revision)

            if diff_content:
                change = {
                    'new_path': os.path.basename(file_path),
                    'diff': diff_content,
                    'action': action,
                    'full_path': file_path,
                    'additions': self._count_additions(diff_content),
                    'deletions': self._count_deletions(diff_content)
                }
                changes.append(change)

        return changes

    def _get_file_content(self, file_path: str, revision: str) -> str:
        """
        获取指定版本的文件内容
        :param file_path: 文件路径
        :param revision: 版本号
        :return: 文件内容
        """
        target_url = f"{self.svn_repo_root_url}{file_path}"
        command = [
            'svn', 'cat',
            '-r', revision,
            target_url
        ]
        
        stdout, stderr, returncode = self._run_svn_command(command, cwd=None)
        
        if returncode != 0:
            logger.error(f"获取文件内容失败 ({target_url}): {stderr}")
            return ""        
        lines = stdout.split('\n')
        diff_lines = [f"+{line}" for line in lines]
        return '\n'.join(diff_lines)
    
    def _is_supported_file(self, file_path: str) -> bool:
        """
        检查文件类型是否受支持
        """
        from biz.utils.default_config import get_env_with_default
        supported_extensions = get_env_with_default('SUPPORTED_EXTENSIONS').split(',')
        return any(file_path.endswith(ext) for ext in supported_extensions)
    
    def _count_additions(self, diff_content: str) -> int:
        """
        统计新增行数
        """
        return len(re.findall(r'^\+(?!\+)', diff_content, re.MULTILINE))
    
    def _count_deletions(self, diff_content: str) -> int:
        """
        统计删除行数
        """
        return len(re.findall(r'^-(?!--)', diff_content, re.MULTILINE))
    
    def _safe_decode(self, binary_data: bytes) -> str:
        """
        安全解码二进制数据，尝试多种编码
        :param binary_data: 二进制数据
        :return: 解码后的字符串
        """
        if not binary_data:
            return ""
        
        encodings_to_try = ['utf-8', 'gbk', 'cp936', 'latin1', 'utf-16']
        
        for encoding in encodings_to_try:
            try:
                return binary_data.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用 utf-8 并替换错误字符
        try:
            return binary_data.decode('utf-8', errors='replace')
        except Exception:
            # 最后的手段：转换为字符串表示
            return str(binary_data)

    def _clean_svn_database(self) -> bool:
        """
        清理SVN工作副本数据库（处理work queue错误）
        :return: 是否成功
        """
        try:
            logger.info("开始清理SVN工作副本数据库...")
            
            # 检查.svn目录
            svn_dir = os.path.join(self.svn_local_path, '.svn')
            if not os.path.exists(svn_dir):
                logger.warning("未找到.svn目录")
                return False
            
            # 需要清理的文件列表
            files_to_clean = [
                'wc.db-lock',  # 锁文件
                'wc.db-wal',   # Write-Ahead Log
                'wc.db-shm'    # Shared Memory
            ]
            
            cleaned_files = []
            for filename in files_to_clean:
                file_path = os.path.join(svn_dir, filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        cleaned_files.append(filename)
                        logger.info(f"已删除 {filename}")
                    except Exception as e:
                        logger.warning(f"删除 {filename} 失败: {e}")
            
            if cleaned_files:
                logger.info(f"已清理SVN数据库文件: {', '.join(cleaned_files)}")
                
                # 尝试重新初始化工作副本
                logger.info("尝试重新初始化工作副本...")
                stdout, stderr, returncode = self._run_svn_command(['svn', 'cleanup'], cwd=self.svn_local_path)
                
                if returncode == 0:
                    logger.info("SVN数据库清理成功")
                    return True
                else:
                    logger.warning(f"cleanup仍然失败: {stderr}")
            
            return False
            
        except Exception as e:
            logger.error(f"清理SVN数据库时发生异常: {e}")
            return False

    def _fix_work_queue_error(self) -> bool:
        """
        修复SVN工作队列错误
        :return: 是否成功
        """
        try:
            logger.info("检测到SVN工作队列错误，开始修复...")
            
            # 1. 先尝试清理数据库
            if self._clean_svn_database():
                return True
            
            # 2. 如果清理失败，尝试强制重置工作副本状态
            logger.info("尝试强制重置工作副本状态...")
            
            # 使用 svn cleanup --remove-unversioned --remove-ignored --include-externals
            stdout, stderr, returncode = self._run_svn_command([
                'svn', 'cleanup', 
                '--remove-unversioned', 
                '--remove-ignored',
                '--include-externals'
            ], cwd=self.svn_local_path)
            
            if returncode == 0:
                logger.info("强制重置工作副本状态成功")
                return True
            
            logger.warning(f"强制重置也失败: {stderr}")
            
            # 3. 最后手段：重建整个工作副本
            logger.info("尝试重建整个工作副本...")
            return self._rebuild_working_copy()
            
        except Exception as e:
            logger.error(f"修复工作队列错误时发生异常: {e}")
            return False

def filter_svn_changes(changes: List[Dict]) -> List[Dict]:
    """
    过滤SVN变更，只保留支持的文件类型
    """
    from biz.utils.default_config import get_env_with_default, is_path_excluded
    supported_extensions = get_env_with_default('SUPPORTED_EXTENSIONS').split(',')
    exclude_patterns = [p.strip() for p in get_env_with_default('EXCLUDE_PATTERNS').split(',') if p.strip()]
    
    filtered_changes = []
    for change in changes:
        path = change.get('new_path', '')
        if not any(path.endswith(ext) for ext in supported_extensions):
            continue
        if is_path_excluded(path, exclude_patterns):
            logger.info(f'文件 {path} 匹配排除规则，跳过审查')
            continue
        filtered_changes.append({
            'diff': change.get('diff', ''),
            'new_path': path,
            'full_path': change.get('full_path', path),
            'action': change.get('action', ''),
            'additions': change.get('additions', 0),
            'deletions': change.get('deletions', 0)
        })
    
    return filtered_changes
