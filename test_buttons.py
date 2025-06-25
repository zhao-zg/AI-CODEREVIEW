import streamlit as st

st.title("按钮测试")

# 测试基本按钮
if st.button("基本按钮"):
    st.write("基本按钮工作正常")

# 测试带key的按钮
if st.button("带key的按钮", key="test_key"):
    st.write("带key的按钮工作正常")

# 测试在列中的按钮
col1, col2, col3 = st.columns(3)

with col1:
    test_btn = st.button("🧪 测试配置", key="test_config_btn_simple")
    if test_btn:
        st.write("测试配置按钮工作正常")

with col2:
    reload_btn = st.button("🔄 重载配置", key="reload_config_btn_simple")
    if reload_btn:
        st.write("重载配置按钮工作正常")

with col3:
    status_btn = st.button("📊 检查状态", key="check_status_btn_simple")
    if status_btn:
        st.write("检查状态按钮工作正常")
