#!/usr/bin/env python3
"""
配置自动监控服务
监听配置文件变化并自动通知相关服务重新加载配置
"""

import os
import sys
import time
import signal
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biz.utils.log import logger


class ConfigMonitorHandler(FileSystemEventHandler):
    """配置文件监控处理器"""
    
    def __init__(self):
        self.last_reload_time = {}
        self.cooldown_seconds = 3  # 3秒冷却时间
        
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # 只处理配置文件
        if not self._is_config_file(file_path):
            return
        
        # 防抖处理
        current_time = time.time()
        last_time = self.last_reload_time.get(str(file_path), 0)
        
        if current_time - last_time < self.cooldown_seconds:
            return
        
        self.last_reload_time[str(file_path)] = current_time
        
        logger.info(f"检测到配置文件变化: {file_path}")
        
        # 延迟处理，避免文件正在写入
        threading.Timer(1.0, self._handle_config_change, args=[file_path]).start()
    
    def _is_config_file(self, file_path: Path) -> bool:
        """判断是否为配置文件"""
        config_files = ['.env', 'dashboard_config.py', 'prompt_templates.yml']
        
        return (
            file_path.name in config_files or
            file_path.suffix in ['.yml', '.yaml'] or
            (file_path.suffix == '.py' and 'config' in file_path.name.lower())
        )
    
    def _handle_config_change(self, file_path: Path):
        """处理配置文件变化"""
        try:
            logger.info(f"处理配置文件变化: {file_path}")
            
            # 重新加载环境变量（如果是.env文件）
            if file_path.name == '.env':
                load_dotenv(file_path, override=True)
                logger.info("环境变量已重新加载")
            
            # 通知相关服务
            self._notify_services(file_path)
            
        except Exception as e:
            logger.error(f"处理配置文件变化失败: {e}")
    
    def _notify_services(self, file_path: Path):
        """通知相关服务重新加载配置"""
        try:
            from biz.utils.config_reloader import ConfigReloader
            reloader = ConfigReloader()
            
            # 执行配置重载
            result = reloader.reload_all_configs()
            
            if result.get("success", False):
                logger.info(f"配置重载成功: {result['message']}")
                
                # 记录详细信息
                details = result.get("details", {})
                services_notified = details.get("services_notified", {})
                
                for service, success in services_notified.items():
                    if success:
                        logger.info(f"  - {service} 服务配置重载成功")
                    else:
                        logger.warning(f"  - {service} 服务配置重载失败")
                        
            else:
                logger.warning(f"配置重载部分成功: {result.get('message', '未知错误')}")
                
        except Exception as e:
            logger.error(f"通知服务重载配置失败: {e}")


class ConfigMonitorService:
    """配置监控服务"""
    
    def __init__(self, config_dir: str = "conf"):
        self.config_dir = Path(config_dir)
        self.observer = None
        self.running = False
        
    def start(self):
        """启动监控服务"""
        if self.running:
            return
        
        try:
            # 创建监控器
            self.observer = Observer()
            handler = ConfigMonitorHandler()
            
            # 监控配置目录
            self.observer.schedule(handler, str(self.config_dir), recursive=True)
            
            # 启动监控
            self.observer.start()
            self.running = True
            
            logger.info(f"配置监控服务已启动，监控目录: {self.config_dir}")
            print(f"🔍 配置监控服务已启动，监控目录: {self.config_dir}")
            
        except Exception as e:
            logger.error(f"启动配置监控服务失败: {e}")
            print(f"❌ 启动配置监控服务失败: {e}")
            raise
    
    def stop(self):
        """停止监控服务"""
        if not self.running:
            return
        
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join()
            
            self.running = False
            logger.info("配置监控服务已停止")
            print("🛑 配置监控服务已停止")
            
        except Exception as e:
            logger.error(f"停止配置监控服务失败: {e}")
            print(f"❌ 停止配置监控服务失败: {e}")
    
    def is_running(self):
        """检查服务是否正在运行"""
        return self.running and self.observer and self.observer.is_alive()


def setup_signal_handlers(monitor_service):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        print(f"\n收到信号 {signum}，正在停止配置监控服务...")
        monitor_service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号


def main():
    """主函数"""
    print("🚀 AI-CodeReview 配置监控服务")
    print("=" * 50)
    
    # 创建监控服务
    monitor_service = ConfigMonitorService()
    
    # 设置信号处理器
    setup_signal_handlers(monitor_service)
    
    try:
        # 启动监控服务
        monitor_service.start()
        
        # 保持服务运行
        print("✅ 配置监控服务正在运行...")
        print("💡 按 Ctrl+C 停止服务")
        print("-" * 50)
        
        while True:
            time.sleep(1)
            
            # 检查服务是否仍在运行
            if not monitor_service.is_running():
                print("⚠️ 监控服务意外停止")
                break
                
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    except Exception as e:
        print(f"\n❌ 配置监控服务异常: {e}")
        logger.error(f"配置监控服务异常: {e}")
    finally:
        monitor_service.stop()


if __name__ == "__main__":
    main()
