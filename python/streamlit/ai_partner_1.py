import os
from openai import OpenAI
import streamlit as st
from dotenv import load_dotenv

load_dotenv(".env")

client = OpenAI(api_key=os.getenv("api_key"), base_url=os.getenv("base_url"))


st.set_page_config(
    page_title="AI智能伴侣",
    page_icon="🤖",
    # 布局
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}
)

# 标题
st.title("AI智能伴侣")

# logo
st.logo("D:/桌面/GitHub/Jianyu-is-learning/python/streamlit/resources/logo.png")


# 初始化聊天信息
if "messages" not in st.session_state:
    st.session_state.messages = []

# 每次请求发送后都会重新加载页面，所以需要在页面加载时渲染所有消息
# 这里使用 for 循环遍历所有消息，渲染每个消息
for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])
    
prompt = st.chat_input("和你的AI智能伴侣聊天：")
if prompt:  # 这里字符串会自动转化为布尔值
    # 用户请求
    st.chat_message("user").write(prompt)
    print("提示词:", prompt)

    # 记录用户请求
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 模型响应
    print(*st.session_state.messages)
    response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个可爱的布偶猫娘，你会温柔耐心地和我对话"},
        *st.session_state.messages,
    ],
    max_tokens=1024,
    temperature=0.7,
    stream=True
    )

    # 对于流式响应，使用一个固定容器来不断更新内容
    response_container = st.empty()

    # 非流式响应
    # llm_relpy = response.choices[0].message.content
    # st.chat_message("assistant").write(llm_relpy)
    # print("模型响应:", llm_relpy)
    
    # 流式响应
    llm_relpy = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            llm_relpy += content
            response_container.write(llm_relpy)
    print(llm_relpy)
            
    # 记录模型响应
    st.session_state.messages.append({"role": "assistant", "content": llm_relpy})
