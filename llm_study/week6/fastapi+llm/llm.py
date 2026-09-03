
from openai import OpenAI
import os

#输入你的apikey
API_KEY=""

def qwen_max(prompt, api_key=API_KEY, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", model_name="qwen-max-latest"): # Corrected model name based on output
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    try:
        completion = client.chat.completions.create(
            model=model_name, # Use the model_name variable
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': prompt}
            ],
            stream=True,
            # stream_options={"include_usage": True} # You can keep or remove this; usage info doesn't usually contain text content chunks
        )

        # Iterate through the stream chunks
        for chunk in completion:
            # Check if choices exist and the delta has content
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                # Extract the text content
                content = chunk.choices[0].delta.content
                # Print the content immediately without a newline
                print(content, end='', flush=True) # flush=True ensures immediate output

        print() # Add a newline at the very end after the stream finishes

    except Exception as e:
        print(f"\nAn error occurred: {e}")



def qwen_qwq(prompt):
    # 初始化OpenAI客户端
    client = OpenAI(
        # 如果没有配置环境变量，请用百炼API Key替换：api_key="sk-xxx"
        api_key = API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""     # 定义完整回复
    is_answering = False   # 判断是否结束思考过程并开始回复

    # 创建聊天完成请求
    completion = client.chat.completions.create(
        model="qwq-32b",  # 此处以 qwq-32b 为例，可按需更换模型名称
        messages=[
            {"role": "user", "content": prompt}
        ],
        # QwQ 模型仅支持流式输出方式调用
        stream=True,
        # 解除以下注释会在最后一个chunk返回Token使用量
        # stream_options={
        #     "include_usage": True
        # }
    )

    print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

    for chunk in completion:
        # 如果chunk.choices为空，则打印usage
        if not chunk.choices:
            print("\nUsage:")
            print(chunk.usage)
        else:
            delta = chunk.choices[0].delta
            # 打印思考过程
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                print(delta.reasoning_content, end='', flush=True)
                reasoning_content += delta.reasoning_content
            else:
                # 开始回复
                if delta.content != "" and is_answering is False:
                    print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                    is_answering = True
                # 打印回复过程
                print(delta.content, end='', flush=True)
                answer_content += delta.content

    # print("=" * 20 + "完整思考过程" + "=" * 20 + "\n")
    # print(reasoning_content)
    # print("=" * 20 + "完整回复" + "=" * 20 + "\n")
    # print(answer_content)


def deepseek_stream(prompt,api_key=API_KEY,base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",model_name="deepseek-r1"):
    # 初始化OpenAI客户端
    client = OpenAI(
    # 如果没有配置环境变量，请用API Key替换：api_key="sk-xxx"
    api_key=api_key,
    base_url=base_url,
    )
    
    
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""     # 定义完整回复
    is_answering = False   # 判断是否结束思考过程并开始回复

    # 创建聊天完成请求
    stream = client.chat.completions.create(
        model=model_name,  # 此处以 deepseek-v3 为例，可按需更换模型名称
        messages=[
            {"role": "user", "content": prompt}
        ],
        stream=True
        # 解除以下注释会在最后一个chunk返回Token使用量
        # stream_options={
        #     "include_usage": True
        # }
    )

    print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

    for chunk in stream:
        # 处理usage信息
        if not getattr(chunk, 'choices', None):
            print("\n" + "=" * 20 + "Token 使用情况" + "=" * 20 + "\n")
            print(chunk.usage)
            continue

        delta = chunk.choices[0].delta

        # 检查是否有reasoning_content属性
        if not hasattr(delta, 'reasoning_content'):
            continue

        # 处理空内容情况
        if not getattr(delta, 'reasoning_content', None) and not getattr(delta, 'content', None):
            continue

        # 处理开始回答的情况
        if not getattr(delta, 'reasoning_content', None) and not is_answering:
            print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
            is_answering = True

        # 处理思考过程
        if getattr(delta, 'reasoning_content', None):
            print(delta.reasoning_content, end='', flush=True)
            reasoning_content += delta.reasoning_content
        # 处理回复内容
        elif getattr(delta, 'content', None):
            print(delta.content, end='', flush=True)
            answer_content += delta.content

    # 如果需要打印完整内容，解除以下的注释
    """
    print("=" * 20 + "完整思考过程" + "=" * 20 + "\n")
    print(reasoning_content)
    print("=" * 20 + "完整回复" + "=" * 20 + "\n")
    print(answer_content)
    """
    
    
if __name__=="__main__":
    prompt='''
    你是谁
    '''

    # deepseek_stream(prompt)

        
    qwen_max(prompt)
    
    # qwen_qwq(prompt)
    