#!/usr/bin/env python3
"""
全面修复ui.py中的缩进问题
"""

import re

def fix_all_indentation():
    # 读取文件
    with open('ui.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    for i, line in enumerate(lines):
        # 计算前导空格数
        leading_spaces = len(line) - len(line.lstrip())
        content = line.lstrip()
        
        # 跳过空行和注释
        if not content or content.startswith('#'):
            fixed_lines.append(line)
            continue
        
        # 修复常见的缩进问题
        if leading_spaces == 18:  # 18个空格改为20个
            fixed_lines.append('                    ' + content)
        elif leading_spaces == 14:  # 14个空格改为16个
            fixed_lines.append('                ' + content)
        else:
            fixed_lines.append(line)
    
    # 写回文件
    with open('ui.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("✅ 修复了所有缩进问题")

def fix_safe_int_usage():
    """确保所有配置解析都使用safe_int"""
    with open('ui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换所有不安全的int(dashboard_config.get(...))调用
    patterns = [
        (r'int\(dashboard_config\.get\("([^"]+)", ([^)]+)\)\)', 
         r'safe_int(dashboard_config.get("\1", \2), \2)'),
    ]
    
    count = 0
    for pattern, replacement in patterns:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            count += len(matches)
    
    # 写回文件
    with open('ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 修复了 {count} 个不安全的int()调用")

if __name__ == "__main__":
    fix_all_indentation()
    fix_safe_int_usage()
    print("🎉 UI修复完成！")
