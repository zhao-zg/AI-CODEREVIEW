import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
from biz.utils.log import logger
from biz.utils.svn_tool import SVNTool


class SVNHandler:
    """SVN版本控制处理器"""
    
    def __init__(self, svn_path: str, svn_username: str = None, svn_password: str = None):
        """
        初始化SVN处理器
        :param svn_path: SVN仓库本地路径
        :param svn_username: SVN用户名
        :param svn_password: SVN密码
        """
        self.svn_path = svn_path
        self.svn_username = svn_username
        self.svn_password = svn_password
        
        # 检查SVN命令是否可用
        if not SVNTool.is_svn_available():
            raise RuntimeError("SVN命令不可用，请检查SVN客户端是否正确安装")
        
        # 初始化SVN工具
        self.svn_tool = SVNTool(svn_path, svn_username, svn_password)
        
        logger.info(f"SVN处理器初始化完成，版本: {SVNTool.get_svn_version()}")
        logger.info(f"工作目录: {svn_path}")
    
    def _run_svn_command(self, command: List[str]) -> Tuple[str, str, int]:
        """
        执行SVN命令
        :param command: SVN命令列表
        :return: (stdout, stderr, returncode)
        """
        try:
            # 添加认证参数
            if self.svn_username and self.svn_password:
                command.extend(['--username', self.svn_username, '--password', self.svn_password])
            
            # 添加非交互模式和信任服务器证书
            command.extend(['--non-interactive', '--trust-server-cert-failures=unknown-ca,cn-mismatch,expired,not-yet-valid,other'])
            
            logger.info(f"执行SVN命令: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=self.svn_path,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            return result.stdout, result.stderr, result.returncode
        
        except Exception as e:
            logger.error(f"执行SVN命令失败: {e}")
            return "", str(e), -1    def update_working_copy(self) -> bool:
        """
        更新SVN工作副本
        :return: 更新是否成功
        """
        logger.info("开始更新SVN工作副本...")
        success = self.svn_tool.update()
        
        if success:
            logger.info("SVN工作副本更新成功")
        else:
            logger.error("SVN工作副本更新失败")
        
        return success
    
    def get_recent_commits(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        获取最近的提交记录
        :param hours: 最近多少小时的提交
        :param limit: 限制提交数量
        :return: 提交记录列表
        """
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 格式化时间为SVN能识别的格式
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        command = [
            'svn', 'log', 
            '--xml',
            '-r', f'{{{start_time_str}}}:{{{end_time_str}}}',
            '-l', str(limit),
            '-v'  # 包含变更的文件信息
        ]
        
        stdout, stderr, returncode = self._run_svn_command(command)
        
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
                
                # 解析变更的文件
                paths = []
                paths_element = logentry.find('paths')
                if paths_element is not None:
                    for path in paths_element.findall('path'):
                        action = path.get('action')
                        file_path = path.text
                        paths.append({
                            'action': action,  # A=添加, M=修改, D=删除
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
    
    def get_file_diff(self, file_path: str, revision1: str, revision2: str = 'HEAD') -> str:
        """
        获取文件的差异
        :param file_path: 文件路径
        :param revision1: 旧版本号
        :param revision2: 新版本号，默认为HEAD
        :return: 差异内容
        """
        command = [
            'svn', 'diff',
            '-r', f'{revision1}:{revision2}',
            os.path.join(self.svn_path, file_path)
        ]
        
        stdout, stderr, returncode = self._run_svn_command(command)
        
        if returncode != 0:
            logger.error(f"获取文件差异失败: {stderr}")
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
            
            # 跳过删除的文件
            if action == 'D':
                continue
            
            # 只处理支持的文件类型
            if not self._is_supported_file(file_path):
                continue
            
            # 获取文件差异
            diff_content = ""
            if action == 'A':  # 新增文件
                # 对于新增文件，获取完整内容
                diff_content = self._get_file_content(file_path, revision)
            elif action == 'M':  # 修改文件
                # 对于修改文件，获取差异
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
        command = [
            'svn', 'cat',
            '-r', revision,
            os.path.join(self.svn_path, file_path)
        ]
        
        stdout, stderr, returncode = self._run_svn_command(command)
        
        if returncode != 0:
            logger.error(f"获取文件内容失败: {stderr}")
            return ""
        
        # 对于新增文件，构造差异格式
        lines = stdout.split('\n')
        diff_lines = [f"+{line}" for line in lines]
        return '\n'.join(diff_lines)
    
    def _is_supported_file(self, file_path: str) -> bool:
        """
        检查文件类型是否受支持
        :param file_path: 文件路径
        :return: 是否支持
        """
        supported_extensions = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql').split(',')
        return any(file_path.endswith(ext) for ext in supported_extensions)
    
    def _count_additions(self, diff_content: str) -> int:
        """
        统计新增行数
        :param diff_content: 差异内容
        :return: 新增行数
        """
        return len(re.findall(r'^\+(?!\+)', diff_content, re.MULTILINE))
    
    def _count_deletions(self, diff_content: str) -> int:
        """
        统计删除行数
        :param diff_content: 差异内容  
        :return: 删除行数
        """
        return len(re.findall(r'^-(?!--)', diff_content, re.MULTILINE))


def filter_svn_changes(changes: List[Dict]) -> List[Dict]:
    """
    过滤SVN变更，只保留支持的文件类型
    :param changes: 变更列表
    :return: 过滤后的变更列表
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
