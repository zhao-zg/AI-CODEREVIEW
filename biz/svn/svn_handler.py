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
            # 使用 . 作为目标，检出到CWD
            command = ['svn', 'checkout', self.svn_remote_url, '.']
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
            
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            return result.stdout, result.stderr, result.returncode
        
        except Exception as e:
            logger.error(f"执行SVN命令失败: {e}")
            return "", str(e), -1
    
    def update_working_copy(self) -> bool:
        """
        更新SVN工作副本
        :return: 更新是否成功
        """
        stdout, stderr, returncode = self._run_svn_command(['svn', 'update'], cwd=self.svn_local_path)
        
        if returncode != 0:
            logger.error(f"SVN更新失败: {stderr}")
            return False
        
        logger.info("SVN工作副本更新成功")
        return True
    
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
    
    def get_commit_changes(self, commit: Dict) -> List[Dict]:
        """
        获取提交的变更内容
        :param commit: 提交信息
        :return: 变更列表
        """
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
        supported_extensions = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql').split(',')
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


def filter_svn_changes(changes: List[Dict]) -> List[Dict]:
    """
    过滤SVN变更，只保留支持的文件类型
    """
    supported_extensions = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql').split(',')
    
    filtered_changes = []
    for change in changes:
        if any(change.get('new_path', '').endswith(ext) for ext in supported_extensions):
            filtered_changes.append({
                'diff': change.get('diff', ''),
                'new_path': change.get('new_path', ''),
                'additions': change.get('additions', 0),
                'deletions': change.get('deletions', 0)
            })
    
    return filtered_changes
