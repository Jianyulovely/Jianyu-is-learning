import streamlit as st

st.set_page_config(
    page_title="拉康精神分析介绍",
    page_icon="🧊",
    # 布局
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://streamlit.io/playground',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

# 标题
st.title("Streamlit 入门演示")
st.header("Streamlit 一级标题")
st.subheader("Streamlit 二级标题")

# 段落文字
st.write("拉康派精神分析是20世纪法国精神分析学家雅克·拉康对弗洛伊德理论的激进重构。")
st.write("拉康提出了三个关键概念：**镜像阶段**——婴儿在镜中认出自己的形象，形成最初的自我（误认）；**三界拓扑**——实在界（无法符号化的原初创伤）、想象界（意象与投射）、象征界（语言、法律与父权秩序）；以及**欲望是他者的欲望**——人的欲望本质上是追求被他人承认、复制他人的欲望对象。")
st.write("治疗目标不是“治愈症状”，而是通过分析让主体识别自己欲望中的无意识结构，承担自身存在的根本缺失（对象a）。拉康派分析强调弹性时间、不固定频率和分析师的“欲望之位置”，对哲学、文学、电影等领域影响深远。")

# 图片插入
st.image("D:/桌面/GitHub/Jianyu-is-learning/python/streamlit/resources/凉皮.jpg", width=300)

# 商标插入
st.logo("D:/桌面/GitHub/Jianyu-is-learning/python/streamlit/resources/西红柿炒鸡蛋.jpg")

# 表格
student_data = {
    "姓名": ["王林", "利姆湾", "贝罗", "茉莉海"],
    "总分": [610, 600, 588, 645]
}
st.table(student_data)

# 输入框
username = st.text_input("输入用户名")
st.write(f"输入的用户名为：{username}")

password = st.text_input("输入密码", type="password")
st.write(f"输入的密码为：{password}")

# 单选按钮
gender = st.radio("请选择性别", ["男", "女", "未知"], index=2)
st.write(f"您的性别是：{gender}")