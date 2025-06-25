#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全局默认配置管理模块
从 .env.dist 文件中读取默认值，避免硬编码
"""

import os
from pathlib import Path
from typing import Dict, Optional

class DefaultConfigManager:
    """默认配置管理器，从 .env.dist 文件中读取默认值"""
    
    _instance = None
    _defaults: Dict[str, str] = {}
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._loaded:
            self._load_defaults()
            self._loaded = True
    
    def _load_defaults(self):
        """从 .env.dist 文件中加载默认值"""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        env_dist_path = project_root / "conf" / ".env.dist"
        
        if not env_dist_path.exists():
            print(f"警告: 找不到 .env.dist 文件: {env_dist_path}")
            return
        
        try:
            with open(env_dist_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析键值对
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = self._unescape_env_value(value.strip())
                        self._defaults[key] = value
                    
        except Exception as e:
            print(f"加载 .env.dist 文件时出错: {e}")
    
    def _unescape_env_value(self, value: str) -> str:
        """解析环境变量值（处理引号和转义）"""
        if not value:
            return ""
        
        # 如果被双引号包围，去掉引号并处理转义
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            inner_value = value[1:-1]
            # 处理转义字符
            inner_value = inner_value.replace('\\"', '"').replace('\\\\', '\\')
            return inner_value
        
        # 如果被单引号包围，去掉引号（单引号内不处理转义）
        elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
            return value[1:-1]
        
        return value
    
    def get_default(self, key: str, fallback: str = "") -> str:
        """获取配置项的默认值"""
        return self._defaults.get(key, fallback)
    
    def get_all_defaults(self) -> Dict[str, str]:
        """获取所有默认配置"""
        return self._defaults.copy()
    
    def reload(self):
        """重新加载默认配置"""
        self._defaults.clear()
        self._loaded = False
        self._load_defaults()
        self._loaded = True

# 全局实例
_default_config = DefaultConfigManager()

def get_env_with_default(key: str, custom_fallback: Optional[str] = None) -> str:
    """
    获取环境变量，使用 .env.dist 中的默认值
    
    Args:
        key: 环境变量名
        custom_fallback: 自定义回退值（如果 .env.dist 中也没有）
    
    Returns:
        环境变量值
    """
    # 首先尝试从环境变量获取
    env_value = os.environ.get(key)
    if env_value is not None:
        return env_value
    
    # 然后从 .env.dist 获取默认值
    default_value = _default_config.get_default(key)
    if default_value:
        return default_value
    
    # 最后使用自定义回退值
    return custom_fallback or ""

def get_env_bool(key: str, custom_fallback: Optional[bool] = None) -> bool:
    """
    获取布尔类型的环境变量
    
    Args:
        key: 环境变量名
        custom_fallback: 自定义回退值
    
    Returns:
        布尔值
    """
    value = get_env_with_default(key)
    if value:
        return value.lower() in ('1', 'true', 'yes', 'on')
    
    return custom_fallback or False

def get_env_int(key: str, custom_fallback: Optional[int] = None) -> int:
    """
    获取整数类型的环境变量
    
    Args:
        key: 环境变量名
        custom_fallback: 自定义回退值
    
    Returns:
        整数值
    """
    value = get_env_with_default(key)
    if value and value.isdigit():
        return int(value)
    
    return custom_fallback or 0

def reload_defaults():
    """重新加载默认配置（用于测试或动态更新）"""
    _default_config.reload()

# 向后兼容的函数名
def get_config_default(key: str, fallback: str = "") -> str:
    """向后兼容的函数名"""
    return get_env_with_default(key, fallback)
