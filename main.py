import streamlit as st

# 项目
liang1 = st.Page("liangliang/liang1.py", title="liang1", icon="🏠")
liang2 = st.Page("liangliang/liang2.py", title="liang2", icon="🏠")
liang3 = st.Page("liangliang/liang3.py", title="liang3", icon="🏠")
liang4 = st.Page("liangliang/liang4.py", title="liang4", icon="🏠")
liang5 = st.Page("liangliang/liang5.py", title="liang5", icon="🏠")
liang6 = st.Page("liangliang/liang6.py", title="liang6", icon="🏠")


# 配置导航（可以分组）
pg = st.navigation({
    # "Demo": [demo0, demo1, demo2, demo3, demo4, animation0, animation1, animation2, animation3, animation4,
    #          animation5, animation6, sidebar1, sidebar2, tab1, tab2, table1, table2
    #          ],
    "项目": [liang1, liang2, liang3,liang4,liang5,liang6],
})

# 执行当前选中的页面
pg.run()
