#!/usr/bin/env python3
"""
修复UI文件中的缩进和int()转换问题
"""

import re

def fix_ui_issues():
    # 读取文件
    with open('ui.py', 'r', encoding='utf-8') as f:
        content = f.read()
      # 修复缩进问题 - 将所有不正确的缩进统一
    # 修复18个空格的缩进为16个空格
    content = re.sub(r'^                  ', '                ', content, flags=re.MULTILINE)
    # 修复14个空格的缩进为16个空格  
    content = re.sub(r'^              ', '                ', content, flags=re.MULTILINE)
    
    # 替换所有不安全的int(dashboard_config.get(...))调用
    patterns = [
        (r'int\(dashboard_config\.get\("MAX_RECORDS_PER_PAGE", (\d+)\)\)', 
         r'safe_int(dashboard_config.get("MAX_RECORDS_PER_PAGE", "\1"), \1)'),
        (r'int\(dashboard_config\.get\("DEFAULT_CHART_HEIGHT", (\d+)\)\)', 
         r'safe_int(dashboard_config.get("DEFAULT_CHART_HEIGHT", "\1"), \1)'),
        (r'int\(dashboard_config\.get\("CACHE_TTL_MINUTES", (\d+)\)\)', 
         r'safe_int(dashboard_config.get("CACHE_TTL_MINUTES", "\1"), \1)'),
        (r'int\(dashboard_config\.get\("AUTO_REFRESH_INTERVAL", (\d+)\)\)', 
         r'safe_int(dashboard_config.get("AUTO_REFRESH_INTERVAL", "\1"), \1)')
    ]
    
    count = 0
    for pattern, replacement in patterns:
        old_content = content
        content = re.sub(pattern, replacement, content)
        if content != old_content:
            count += 1
    
    # 写回文件
    with open('ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 修复了缩进问题")
    print(f"✅ 替换了 {count} 个不安全的int()调用")
    return True

if __name__ == "__main__":
    fix_ui_issues()
