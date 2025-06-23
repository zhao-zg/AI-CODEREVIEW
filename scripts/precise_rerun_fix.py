#!/usr/bin/env python3
"""
精确修复ui.py中的特定st.rerun()调用，避免破坏缩进
"""

def precise_fix_rerun():
    """精确修复st.rerun()调用"""
    
    # 读取文件
    with open('ui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到所有st.rerun()调用的位置，但排除st_rerun函数定义内的
    import re
    
    # 先找到st_rerun函数的定义范围
    st_rerun_func_start = content.find('def st_rerun():')
    st_rerun_func_end = content.find('\n\n', st_rerun_func_start) if st_rerun_func_start != -1 else -1
    
    if st_rerun_func_start == -1:
        print("❌ 找不到st_rerun函数定义")
        return False
    
    print(f"📍 st_rerun函数定义范围: {st_rerun_func_start} - {st_rerun_func_end}")
    
    # 查找所有st.rerun()调用
    pattern = r'st\.rerun\(\)'
    matches = list(re.finditer(pattern, content))
    
    print(f"📊 找到 {len(matches)} 个 st.rerun() 调用")
    
    # 从后往前替换，避免位置偏移
    count = 0
    for match in reversed(matches):
        pos = match.start()
        # 检查是否在st_rerun函数定义内
        if st_rerun_func_start <= pos <= st_rerun_func_end:
            print(f"⏭️  跳过st_rerun函数内的调用 (位置: {pos})")
            continue
        
        # 替换这个调用
        content = content[:pos] + 'st_rerun()' + content[match.end():]
        count += 1
        print(f"✅ 替换位置 {pos} 的 st.rerun() -> st_rerun()")
    
    # 写回文件
    with open('ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"🎯 总共修复 {count} 个 st.rerun() 调用")
    
    # 验证语法
    try:
        import py_compile
        py_compile.compile('ui.py', doraise=True)
        print("✅ Python语法检查通过")
        return True
    except Exception as e:
        print(f"❌ 语法错误: {e}")
        return False

if __name__ == "__main__":
    success = precise_fix_rerun()
    if success:
        print("🎉 精确修复完成！")
    else:
        print("❌ 修复失败")
