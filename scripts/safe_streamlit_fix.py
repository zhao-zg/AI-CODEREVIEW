#!/usr/bin/env python3
"""
安全地修复ui.py中的st.rerun()调用，保持文件编码不变
"""

import re

def safe_fix_streamlit_rerun():
    """安全地修复st.rerun()调用"""
    try:
        # 尝试用UTF-8读取
        with open('ui.py', 'r', encoding='utf-8') as f:
            content = f.read()
        encoding = 'utf-8'
    except UnicodeDecodeError:
        try:
            # 尝试用GBK读取
            with open('ui.py', 'r', encoding='gbk') as f:
                content = f.read()
            encoding = 'gbk'
        except UnicodeDecodeError:
            # 最后尝试latin1
            with open('ui.py', 'r', encoding='latin1') as f:
                content = f.read()
            encoding = 'latin1'
    
    print(f"✅ 使用 {encoding} 编码成功读取文件")
    
    # 只替换代码中的st.rerun()调用，不替换函数定义内的调用
    # 使用更精确的正则表达式
    patterns = [
        # 匹配非函数定义内的st.rerun()调用
        (r'(\s+)st\.rerun\(\)', r'\1st_rerun()'),
    ]
    
    count = 0
    for pattern, replacement in patterns:
        matches = re.findall(pattern, content)
        if matches:
            old_content = content
            content = re.sub(pattern, replacement, content)
            # 确保st_rerun函数定义内的st.rerun()不被替换
            content = content.replace('if hasattr(st, \'rerun\'):\n            st_rerun()', 
                                    'if hasattr(st, \'rerun\'):\n            st.rerun()')
            if content != old_content:
                count += len(matches)
    
    # 用相同编码写回文件
    with open('ui.py', 'w', encoding=encoding) as f:
        f.write(content)
    
    print(f"✅ 已替换 {count} 个 st.rerun() 调用为 st_rerun()")
    print(f"✅ 保持原始编码: {encoding}")

if __name__ == "__main__":
    safe_fix_streamlit_rerun()
