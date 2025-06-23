#!/usr/bin/env python3
"""
批量替换UI文件中的st.rerun()调用以兼容旧版本Streamlit
"""

import re

def fix_streamlit_rerun():
    # 读取文件
    with open('ui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 计数替换次数
    count = len(re.findall(r'st\.rerun\(\)', content))
    
    # 替换所有的 st.rerun() 为 st_rerun()
    content = re.sub(r'st\.rerun\(\)', 'st_rerun()', content)
    
    # 写回文件
    with open('ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已替换 {count} 个 st.rerun() 调用为 st_rerun()")
    return count

if __name__ == "__main__":
    fix_streamlit_rerun()
