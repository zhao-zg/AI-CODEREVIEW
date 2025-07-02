#!/usr/bin/env python3
"""
配置热重载管理器
实现配置更改后的实时生效功能
"""

import os
import sys
import json
import signal
import psutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ConfigReloader:
    """配置热重载器"""
    
    def __init__(self):
        self.config_dir = Path("conf")
        self.env_file = self.config_dir / ".env"
        self.dashboard_config_file = self.config_dir / "dashboard_config.py"
        self.last_reload_time = 0  # 初始化为0，允许第一次调用
        self.reload_cooldown = 3  # 调整为3秒冷却时间，避免过于频繁的提示
        
    def reload_environment_variables(self) -> bool:
        """重新加载环境变量"""
        try:
            if not self.env_file.exists():
                return False
            
            # 清除现有的环境变量（只清除我们管理的）
            managed_keys = self._get_managed_env_keys()
            for key in managed_keys:
                if key in os.environ:
                    del os.environ[key]
            
            # 重新加载环境变量
            from dotenv import load_dotenv
            load_dotenv(self.env_file, override=True)
            
            print(f"[ConfigReloader] 环境变量已重新加载: {self.env_file}")
            return True
            
        except Exception as e:
            print(f"[ConfigReloader] 重新加载环境变量失败: {e}")
            return False
    
    def _get_managed_env_keys(self) -> List[str]:
        """获取我们管理的环境变量键"""
        return [
            # AI模型配置
            "LLM_PROVIDER", "OPENAI_API_KEY", "OPENAI_API_BASE", "DEEPSEEK_API_KEY",
            "DEEPSEEK_API_BASE", "ZHIPUAI_API_KEY", "QWEN_API_KEY", "OLLAMA_API_BASE_URL",
            "OLLAMA_MODEL", "REVIEW_STYLE", "REVIEW_MAX_TOKENS",
            
            # 平台配置
            "SVN_CHECK_ENABLED", "GITLAB_ENABLED", "GITHUB_ENABLED",
            "GITLAB_URL", "GITLAB_ACCESS_TOKEN", "GITHUB_ACCESS_TOKEN",
            
            # 系统配置
            "SERVER_PORT", "LOG_LEVEL", "QUEUE_DRIVER",
            "REDIS_HOST", "REDIS_PORT",
            
            # 消息推送配置
            "DINGTALK_ENABLED", "DINGTALK_WEBHOOK_URL",
            "WECOM_ENABLED", "WECOM_WEBHOOK_URL",
            "FEISHU_ENABLED", "FEISHU_WEBHOOK_URL",
            
            # 仪表板配置
            "DASHBOARD_USER", "DASHBOARD_PASSWORD"
        ]
    
    def notify_services_config_changed(self) -> Dict[str, bool]:
        """通知所有服务配置已更改"""
        results = {}
        
        # 通知API服务
        results['api'] = self._notify_api_service()
        
    def _notify_services(self) -> dict:
        """通知所有服务重新加载配置"""
        results = {}
        
        # 通知API服务
        results['api'] = self._notify_api_service()
        
        # 通知UI服务
        results['ui'] = self._notify_ui_service()
        
        return results
        
        # 通知UI服务 (Streamlit)
        results['ui'] = self._notify_ui_service()
        
        return results
    
    def _notify_api_service(self) -> bool:
        """通知API服务重新加载配置"""
        try:
            # 在Windows上使用API端点，在Unix上使用信号
            if os.name == 'nt':  # Windows
                return self._notify_api_via_http()
            else:  # Unix/Linux
                return self._notify_api_via_signal()
                
        except Exception as e:
            print(f"[ConfigReloader] 通知API服务失败: {e}")
            return False
    
    def _notify_api_via_signal(self) -> bool:
        """通过信号通知API服务（Unix/Linux）"""
        try:
            # 查找API进程
            api_processes = self._find_processes_by_name('api.py')
            
            for proc in api_processes:
                try:
                    # 发送USR1信号来触发配置重载
                    if hasattr(signal, 'SIGUSR1'):
                        proc.send_signal(signal.SIGUSR1)
                        print(f"[ConfigReloader] 已通知API服务重载配置: PID {proc.pid}")
                except Exception as e:
                    print(f"[ConfigReloader] 通知API服务失败: {e}")
                    
            return len(api_processes) > 0
            
        except Exception as e:
            print(f"[ConfigReloader] 查找API服务失败: {e}")
            return False
    
    def _notify_api_via_http(self) -> bool:
        """通过HTTP端点通知API服务（Windows）"""
        try:
            import requests
            
            # 获取API服务地址
            api_url_base = os.environ.get('API_URL', 'http://localhost:5001')
            api_url = f"{api_url_base}/reload-config"
            
            # 发送POST请求
            response = requests.post(api_url, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    print(f"[ConfigReloader] API服务配置重载成功")
                    return True
                else:
                    print(f"[ConfigReloader] API服务配置重载失败: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"[ConfigReloader] API服务响应异常: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ConfigReloader] 通过HTTP通知API服务失败: {e}")
            return False
    
    # 移除 _notify_worker_processes 方法 - 单服务架构不需要独立 worker 进程
    
    def _notify_ui_service(self) -> bool:
        """通知UI服务配置已更改"""
        try:
            # Streamlit 进程比较特殊，我们通过文件标记的方式来通知
            reload_flag_file = self.config_dir / ".ui_reload_flag"
            
            with open(reload_flag_file, 'w') as f:
                f.write(str(time.time()))
            
            print(f"[ConfigReloader] 已标记UI服务需要重载配置")
            return True
            
        except Exception as e:
            print(f"[ConfigReloader] 通知UI服务失败: {e}")
            return False
    
    def _find_processes_by_name(self, script_name: str) -> List[psutil.Process]:
        """根据脚本名称查找进程"""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and any(script_name in cmd for cmd in cmdline):
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            print(f"[ConfigReloader] 查找进程失败: {e}")
            
        return processes
    
    def reload_all_configs(self) -> Dict[str, Any]:
        """重新加载所有配置并通知服务"""
        current_time = time.time()
        
        # 检查冷却时间
        if current_time - self.last_reload_time < self.reload_cooldown:
            remaining_time = self.reload_cooldown - (current_time - self.last_reload_time)
            return {
                "success": False,
                "message": f"重载过于频繁，请等待 {remaining_time:.1f} 秒后再试",
                "details": {}
            }
        
        # 立即更新最后重载时间，避免并发调用时的冷却问题
        self.last_reload_time = current_time
        
        result = {
            "success": True,
            "message": "配置重载完成",
            "details": {
                "env_reloaded": False,
                "services_notified": {}
            }
        }
        
        try:
            # 重新加载环境变量
            result["details"]["env_reloaded"] = self.reload_environment_variables()
            
            # 通知服务
            result["details"]["services_notified"] = self.notify_services_config_changed()
            
            # 检查是否有服务需要重启
            needs_restart = self._check_services_need_restart()
            if needs_restart:
                result["message"] += "，部分配置可能需要重启服务才能完全生效"
                result["details"]["needs_restart"] = needs_restart
            
        except Exception as e:
            result["success"] = False
            result["message"] = f"配置重载失败: {e}"
        
        return result
    
    def _check_services_need_restart(self) -> List[str]:
        """检查哪些服务需要重启才能使配置生效"""
        restart_needed = []
        
        # 检查端口配置是否更改（需要重启）
        current_port = os.environ.get('SERVER_PORT', '5001')
        if hasattr(self, '_last_port') and self._last_port != current_port:
            restart_needed.append('API服务 (端口配置更改)')
        self._last_port = current_port
        
        # 检查队列驱动是否更改（需要重启）
        current_queue = os.environ.get('QUEUE_DRIVER', 'memory')
        if hasattr(self, '_last_queue') and self._last_queue != current_queue:
            restart_needed.append('Worker进程 (队列驱动更改)')
        self._last_queue = current_queue
        
        return restart_needed


class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监控器"""
    
    def __init__(self, reloader: ConfigReloader):
        self.reloader = reloader
        self.last_reload = 0
        self.reload_delay = 1  # 1秒延迟，避免多次快速触发
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        # 只处理我们关心的配置文件
        if event.src_path.endswith(('.env', '.py', '.yml', '.yaml')):
            current_time = time.time()
            
            # 防抖处理
            if current_time - self.last_reload < self.reload_delay:
                return
            
            self.last_reload = current_time
            
            print(f"[ConfigWatcher] 检测到配置文件变更: {event.src_path}")
            
            # 延迟执行重载
            import threading
            threading.Timer(self.reload_delay, self._delayed_reload).start()
    
    def _delayed_reload(self):
        """延迟执行的重载操作"""
        try:
            result = self.reloader.reload_all_configs()
            if result["success"]:
                print(f"[ConfigWatcher] {result['message']}")
            else:
                print(f"[ConfigWatcher] 重载失败: {result['message']}")
        except Exception as e:
            print(f"[ConfigWatcher] 重载过程中发生异常: {e}")


def start_config_watcher():
    """启动配置文件监控器"""
    reloader = ConfigReloader()
    
    # 创建文件监控器
    event_handler = ConfigFileWatcher(reloader)
    observer = Observer()
    observer.schedule(event_handler, str(reloader.config_dir), recursive=True)
    
    try:
        observer.start()
        print(f"[ConfigWatcher] 配置文件监控器已启动，监控目录: {reloader.config_dir}")
        
        # 保持监控器运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("[ConfigWatcher] 收到中断信号，正在停止监控器...")
        observer.stop()
    
    observer.join()
    print("[ConfigWatcher] 配置文件监控器已停止")


def reload_config_manually():
    """手动重载配置"""
    reloader = ConfigReloader()
    result = reloader.reload_all_configs()
    
    print(f"手动重载结果: {result['message']}")
    if result["details"]:
        print(f"详细信息: {json.dumps(result['details'], indent=2, ensure_ascii=False)}")
    
    return result["success"]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        # 启动监控模式
        start_config_watcher()
    else:
        # 手动重载模式
        success = reload_config_manually()
        sys.exit(0 if success else 1)
