#!/usr/bin/env python3
"""
修复所有st.rerun()调用为st_rerun()以兼容旧版本Streamlit
"""

def fix_streamlit_rerun():
    # 读取文件，尝试不同编码
    encodings = ['utf-8', 'gbk', 'utf-8-sig', 'latin1']
    content = None
    
    for encoding in encodings:
        try:
            with open('ui.py', 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✅ 使用 {encoding} 编码成功读取文件")
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        print("❌ 无法读取文件")
        return
    
    # 替换所有st.rerun()为st_rerun()
    count = content.count('st.rerun()')
    content = content.replace('st.rerun()', 'st_rerun()')
    
    # 写回文件
    with open('ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已替换 {count} 个 st.rerun() 调用为 st_rerun()")

if __name__ == "__main__":
    fix_streamlit_rerun()
