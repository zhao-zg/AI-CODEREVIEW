#!/usr/bin/env python3
"""
配置管理模块
用于在前端UI中管理系统配置
"""

import os
import json
import yaml
import re
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "conf"):
        self.config_dir = Path(config_dir)
        self.env_file = self.config_dir / ".env"
        self.env_dist_file = Path("conf_templates") / ".env.dist"  # 修正路径到conf_templates
        self.dashboard_config_file = self.config_dir / "dashboard_config.py"
        self.prompt_config_file = self.config_dir / "prompt_templates.yml"
    
    @staticmethod
    def _escape_env_value(value: str) -> str:
        """
        安全地转义环境变量值
        处理包含特殊字符的值，如双引号、换行符等
        """
        if not value:
            return ""
        
        # 如果值已经被引号包围，先去掉外层引号
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        
        # 检查是否需要加引号的条件
        needs_quotes = any([
            ' ' in value,      # 包含空格
            '"' in value,      # 包含双引号
            "'" in value,      # 包含单引号
            '\n' in value,     # 包含换行
            '\r' in value,     # 包含回车
            '\t' in value,     # 包含制表符
            value.startswith('#'),  # 以#开头
            '=' in value,      # 包含等号
            value != value.strip(),  # 前后有空白
        ])
        
        if needs_quotes:
            # 转义内部的双引号和反斜杠
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped_value}"'
        
        return value
    
    @staticmethod
    def _unescape_env_value(value: str) -> str:
        """
        安全地解析环境变量值
        处理被引号包围和转义的值
        """
        if not value:
            return ""
        
        value = value.strip()
        
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
    
    def get_env_config(self) -> Dict[str, str]:
        """获取环境变量配置"""
        config = {}
          # 首先从.env.dist获取所有可用的配置项和默认值
        if self.env_dist_file.exists():
            with open(self.env_dist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = self._unescape_env_value(value)
                        config[key] = value
        
        # 然后从.env获取实际值
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = self._unescape_env_value(value)
                        config[key] = value
        
        return config
    
    def save_env_config(self, config: Dict[str, str]) -> bool:
        """保存环境变量配置"""
        try:
            # 创建配置目录
            self.config_dir.mkdir(exist_ok=True)
            
            # 备份现有文件
            if self.env_file.exists():
                backup_file = self.env_file.with_suffix('.env.backup')
                import shutil
                shutil.copy2(self.env_file, backup_file)
            
            # 写入新配置
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write("# AI代码审查系统配置文件\n")
                f.write("# 该文件由配置管理界面自动生成\n\n")
                  # 按分类组织配置
                categories = self._categorize_config(config)
                
                for category, items in categories.items():
                    f.write(f"# {category}\n")
                    for key, value in items.items():
                        escaped_value = self._escape_env_value(value)
                        f.write(f"{key}={escaped_value}\n")
                    f.write("\n")
            
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def _categorize_config(self, config: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """将配置项按类别分组"""
        categories = {
            "AI模型配置": {},
            "数据库配置": {},
            "GitLab配置": {},
            "GitHub配置": {},
            "SVN配置": {},
            "消息推送配置": {},
            "仪表板配置": {},
            "系统配置": {}
        }
        
        # 配置项分类映射
        category_mapping = {
            # AI模型相关
            "LLM_PROVIDER": "AI模型配置",
            "OPENAI_API_KEY": "AI模型配置",
            "OPENAI_API_BASE": "AI模型配置",
            "DEEPSEEK_API_KEY": "AI模型配置",
            "DEEPSEEK_API_BASE": "AI模型配置",
            "ZHIPUAI_API_KEY": "AI模型配置",
            "QWEN_API_KEY": "AI模型配置",
            "OLLAMA_API_BASE_URL": "AI模型配置",
            "OLLAMA_MODEL": "AI模型配置",
            
            # 数据库相关
            "DATABASE_PATH": "数据库配置",
            "DATABASE_URL": "数据库配置",
            
            # GitLab相关
            "GITLAB_ACCESS_TOKEN": "GitLab配置",
            "GITLAB_URL": "GitLab配置",
            "GITLAB_WEBHOOK_SECRET": "GitLab配置",
            
            # GitHub相关
            "GITHUB_ACCESS_TOKEN": "GitHub配置",
            "GITHUB_WEBHOOK_SECRET": "GitHub配置",
            
            # SVN相关
            "SVN_REPOSITORIES": "SVN配置",
            "SVN_USERNAME": "SVN配置",
            "SVN_PASSWORD": "SVN配置",
            "SUPPORTED_EXTENSIONS": "SVN配置",
            "EXCLUDE_PATTERNS": "SVN配置",
            
            # 消息推送相关
            "DINGTALK_ENABLED": "消息推送配置",
            "DINGTALK_WEBHOOK_URL": "消息推送配置",
            "FEISHU_ENABLED": "消息推送配置",
            "FEISHU_WEBHOOK_URL": "消息推送配置",
            "WECOM_ENABLED": "消息推送配置",
            "WECOM_WEBHOOK_URL": "消息推送配置",            # 仪表板相关
            "DASHBOARD_USER": "仪表板配置",
            "DASHBOARD_PASSWORD": "仪表板配置",
            "DASHBOARD_PORT": "仪表板配置",
            
            # 系统配置
            "LOG_LEVEL": "系统配置",
            "API_PORT": "系统配置"        }
        
        # 分类配置项
        for key, value in config.items():
            category = category_mapping.get(key, "系统配置")
            categories[category][key] = value
        
        # 移除空分类
        return {k: v for k, v in categories.items() if v}
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """获取仪表板配置"""
        try:
            if self.dashboard_config_file.exists():
                # 更安全的方式：直接导入Python模块
                import importlib.util
                import sys
                
                # 动态导入配置模块
                spec = importlib.util.spec_from_file_location("dashboard_config", self.dashboard_config_file)
                if spec and spec.loader:
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    
                    # 提取配置变量
                    config = {}
                    for attr_name in dir(config_module):
                        if not attr_name.startswith('_'):
                            attr_value = getattr(config_module, attr_name)
                            # 只处理简单类型的配置项
                            if isinstance(attr_value, (str, int, float, bool, list, dict)):
                                config[attr_name] = attr_value
                    
                    return config
                else:
                    return self._get_default_dashboard_config()
            else:
                return self._get_default_dashboard_config()
        except Exception:
            return self._get_default_dashboard_config()
    
    def _get_default_dashboard_config(self) -> Dict[str, Any]:
        """获取默认仪表板配置"""
        return {
            "DASHBOARD_TITLE": "AI 代码审查仪表板",
            "DASHBOARD_ICON": "🤖",
            "DASHBOARD_LAYOUT": "wide",
            "CHART_COLORS": '["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57"]',
            "MAX_RECORDS_PER_PAGE": "100",
            "DEFAULT_CHART_HEIGHT": "400",
            "ENABLE_CACHING": "True",
            "CACHE_TTL_MINUTES": "15",
            "AUTO_REFRESH_INTERVAL": "300"
        }
    
    def save_dashboard_config(self, config: Dict[str, Any]) -> bool:
        """保存仪表板配置"""
        try:
            self.config_dir.mkdir(exist_ok=True)
            
            # 备份现有文件
            if self.dashboard_config_file.exists():
                backup_file = self.dashboard_config_file.with_suffix('.py.backup')
                import shutil
                shutil.copy2(self.dashboard_config_file, backup_file)
            
            # 写入新配置
            with open(self.dashboard_config_file, 'w', encoding='utf-8') as f:
                f.write('#!/usr/bin/env python3\n')
                f.write('"""\n')
                f.write('仪表板配置文件\n')
                f.write('该文件由配置管理界面自动生成\n')
                f.write('"""\n\n')
                
                # 写入配置项
                for key, value in config.items():
                    if key == "CHART_COLORS":
                        f.write(f'{key} = {value}\n')
                    elif value in ['True', 'False']:
                        f.write(f'{key} = {value}\n')
                    elif value.isdigit():
                        f.write(f'{key} = {value}\n')
                    else:
                        f.write(f'{key} = "{value}"\n')
            
            return True
        except Exception as e:
            print(f"保存仪表板配置失败: {e}")
            return False
    
    def get_prompt_config(self) -> Dict[str, Any]:
        """获取提示模板配置"""
        try:
            if self.prompt_config_file.exists():
                with open(self.prompt_config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            else:
                return self._get_default_prompt_config()
        except Exception:
            return self._get_default_prompt_config()
    
    def _get_default_prompt_config(self) -> Dict[str, Any]:
        """获取默认提示模板配置"""
        return {
            "review_prompt": {
                "system": "你是一个专业的代码审查助手。",
                "user": "请审查以下代码变更：{code_diff}"
            },
            "summary_prompt": {
                "system": "你是一个代码摘要助手。",
                "user": "请为以下代码变更生成摘要：{code_diff}"
            }
        }
    
    def save_prompt_config(self, config: Dict[str, Any]) -> bool:
        """保存提示模板配置"""
        try:
            self.config_dir.mkdir(exist_ok=True)
            
            # 备份现有文件
            if self.prompt_config_file.exists():
                backup_file = self.prompt_config_file.with_suffix('.yml.backup')
                import shutil
                shutil.copy2(self.prompt_config_file, backup_file)
            
            # 写入新配置
            with open(self.prompt_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            print(f"保存提示模板配置失败: {e}")
            return False
    
    def test_config(self, config_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试配置有效性"""
        result = {"success": True, "message": "配置测试通过", "details": []}
        
        try:
            if config_type == "env":
                result = self._test_env_config(config)
            elif config_type == "dashboard":
                result = self._test_dashboard_config(config)
            elif config_type == "prompt":
                result = self._test_prompt_config(config)
        except Exception as e:
            result = {
                "success": False,
                "message": f"配置测试失败: {str(e)}",
                "details": []
            }
        
        return result
    
    def _test_env_config(self, config: Dict[str, str]) -> Dict[str, Any]:
        """测试环境变量配置"""
        result = {"success": True, "message": "环境配置测试通过", "details": []}
        
        # 测试必要的配置项
        required_configs = {
            "LLM_PROVIDER": "AI模型提供商",
            "DASHBOARD_USER": "仪表板用户名",
            "DASHBOARD_PASSWORD": "仪表板密码"
        }
        
        for key, desc in required_configs.items():
            if not config.get(key):
                result["success"] = False
                result["details"].append(f"缺少必要配置: {desc} ({key})")
        
        # 测试API密钥
        llm_provider = config.get("LLM_PROVIDER", "").lower()
        if llm_provider == "openai" and not config.get("OPENAI_API_KEY"):
            result["success"] = False
            result["details"].append("选择OpenAI但未配置API密钥")
        elif llm_provider == "deepseek" and not config.get("DEEPSEEK_API_KEY"):
            result["success"] = False
            result["details"].append("选择DeepSeek但未配置API密钥")
        
        if not result["success"]:
            result["message"] = "环境配置测试失败"
        
        return result
    
    def _test_dashboard_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试仪表板配置"""
        result = {"success": True, "message": "仪表板配置测试通过", "details": []}
        
        # 验证必要配置
        if not config.get("DASHBOARD_TITLE"):
            result["success"] = False
            result["details"].append("仪表板标题不能为空")
        
        # 验证数值配置
        numeric_configs = ["MAX_RECORDS_PER_PAGE", "DEFAULT_CHART_HEIGHT", "CACHE_TTL_MINUTES", "AUTO_REFRESH_INTERVAL"]
        for key in numeric_configs:
            value = config.get(key, "")
            if value and not str(value).isdigit():
                result["success"] = False
                result["details"].append(f"{key} 必须是数字")
        
        if not result["success"]:
            result["message"] = "仪表板配置测试失败"
        
        return result
    
    def _test_prompt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试提示模板配置"""
        result = {"success": True, "message": "提示模板配置测试通过", "details": []}
        
        # 验证必要的提示模板
        required_prompts = ["review_prompt", "summary_prompt"]
        for prompt_name in required_prompts:
            if prompt_name not in config:
                result["success"] = False
                result["details"].append(f"缺少提示模板: {prompt_name}")
            else:
                prompt_config = config[prompt_name]
                if not isinstance(prompt_config, dict):
                    result["success"] = False
                    result["details"].append(f"提示模板 {prompt_name} 格式错误")
                elif "system" not in prompt_config or "user" not in prompt_config:
                    result["success"] = False
                    result["details"].append(f"提示模板 {prompt_name} 缺少system或user字段")
        
        if not result["success"]:
            result["message"] = "提示模板配置测试失败"
        
        return result
    
    def export_config(self, config_type: str) -> Optional[str]:
        """导出配置文件内容"""
        try:
            if config_type == "env":
                if self.env_file.exists():
                    with open(self.env_file, 'r', encoding='utf-8') as f:
                        return f.read()
            elif config_type == "dashboard":
                if self.dashboard_config_file.exists():
                    with open(self.dashboard_config_file, 'r', encoding='utf-8') as f:
                        return f.read()
            elif config_type == "prompt":
                if self.prompt_config_file.exists():
                    with open(self.prompt_config_file, 'r', encoding='utf-8') as f:
                        return f.read()
        except Exception:
            pass
        
        return None
    
    def get_config_help(self, config_key: str) -> str:
        """获取配置项帮助信息"""
        help_texts = {
            # AI模型配置
            "LLM_PROVIDER": "AI模型提供商，支持: openai, deepseek, zhipuai, qwen, ollama",
            "OPENAI_API_KEY": "OpenAI API密钥，从OpenAI官网获取",
            "OPENAI_API_BASE": "OpenAI API基础URL，默认为官方地址",
            "DEEPSEEK_API_KEY": "DeepSeek API密钥，从DeepSeek官网获取",
            "DEEPSEEK_API_BASE": "DeepSeek API基础URL",
            "ZHIPUAI_API_KEY": "智谱AI API密钥",
            "QWEN_API_KEY": "通义千问API密钥",
            "OLLAMA_API_BASE_URL": "Ollama服务地址，如: http://localhost:11434",
            "OLLAMA_MODEL": "Ollama模型名称，如: llama2, codellama",
            
            # GitLab配置
            "GITLAB_ACCESS_TOKEN": "GitLab访问令牌，用于API调用",
            "GITLAB_URL": "GitLab服务器地址",
            "GITLAB_WEBHOOK_SECRET": "GitLab Webhook密钥",
            
            # GitHub配置
            "GITHUB_ACCESS_TOKEN": "GitHub访问令牌",
            "GITHUB_WEBHOOK_SECRET": "GitHub Webhook密钥",
            
            # SVN配置
            "SVN_REPOSITORIES": "SVN仓库配置，JSON格式",
            "SVN_USERNAME": "SVN用户名",
            "SVN_PASSWORD": "SVN密码",
            "SUPPORTED_EXTENSIONS": "支持的文件扩展名，逗号分隔",
            "EXCLUDE_PATTERNS": "排除的文件路径模式，逗号分隔。支持通配符*，如 *.pb.go 过滤proto生成文件；generated/ 过滤任意层级的generated目录；vendor/* 过滤vendor目录",
            
            # 消息推送配置
            "DINGTALK_ENABLED": "是否启用钉钉推送，1启用/0禁用",
            "DINGTALK_WEBHOOK_URL": "钉钉机器人Webhook地址",
            "FEISHU_ENABLED": "是否启用飞书推送，1启用/0禁用",
            "FEISHU_WEBHOOK_URL": "飞书机器人Webhook地址",
            "WECOM_ENABLED": "是否启用企业微信推送，1启用/0禁用",
            "WECOM_WEBHOOK_URL": "企业微信机器人Webhook地址",
            
            # 仪表板配置
            "DASHBOARD_USER": "仪表板登录用户名",
            "DASHBOARD_PASSWORD": "仪表板登录密码",
            "DASHBOARD_PORT": "仪表板服务端口",
            
            # 系统配置
            "LOG_LEVEL": "日志级别: DEBUG, INFO, WARNING, ERROR",
            "API_PORT": "API服务端口，默认5001",
            "DATABASE_PATH": "数据库文件路径"
        }
        
        return help_texts.get(config_key, "暂无帮助信息")
    
    def reset_env_config(self) -> bool:
        """重置环境配置为默认值"""
        try:
            # 如果存在.env.dist文件，复制它到.env
            if self.env_dist_file.exists():
                import shutil
                shutil.copy2(self.env_dist_file, self.env_file)
                return True
            else:
                # 如果没有.env.dist，创建一个基础的.env文件
                default_config = {
                    "FLASK_HOST": "0.0.0.0",
                    "FLASK_PORT": "5000",
                    "DASHBOARD_USER": "admin",
                    "DASHBOARD_PASSWORD": "admin",
                    "DATABASE_PATH": "data/data.db",
                    "LOG_LEVEL": "INFO",
                    "SUPPORTED_EXTENSIONS": ".py,.js,.ts,.java,.cpp,.c,.h,.cs,.php,.rb,.go,.rs,.swift,.kt,.scala,.lua"
                }
                return self.save_env_config(default_config)
        except Exception as e:
            print(f"重置配置失败: {e}")
            return False
