#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径配置工具模块
确保Python能正确找到项目中的所有模块
"""

import sys
import os
from pathlib import Path

def setup_project_path():
    """
    设置项目路径，确保所有模块都能被正确导入
    """
    # 获取项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    
    # 添加项目根目录到Python路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    # 添加ui_components目录
    ui_components_path = project_root / "ui_components"
    ui_components_str = str(ui_components_path)
    if ui_components_str not in sys.path:
        sys.path.insert(0, ui_components_str)
    
    # 添加biz目录
    biz_path = project_root / "biz"
    biz_str = str(biz_path)
    if biz_str not in sys.path:
        sys.path.insert(0, biz_str)
    
    return project_root_str

def get_project_root():
    """
    获取项目根目录路径
    """
    current_file = Path(__file__).resolve()
    return str(current_file.parent)

# 自动执行路径设置
if __name__ != "__main__":
    setup_project_path()
