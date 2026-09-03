from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import json
from typing import Generator

app = FastAPI(title="AI教师助手", description="基于大语言模型的学科教师问答系统")

# 添加CORS中间件，支持前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求体模型
class QuestionRequest(BaseModel):
    question: str

def qwen_max_stream(prompt: str, system_prompt: str = "You are a helpful assistant.", 
                   api_key: str = "sk-f02db5a079ab41588b1cab09ad2777a2", 
                   base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1", 
                   model_name: str = "qwen-max-latest") -> Generator[str, None, None]:
    """
    修改后的qwen_max函数，返回生成器以支持流式响应
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ],
            stream=True,
        )

        # 遍历流式响应块
        for chunk in completion:
            # 检查是否存在choices和delta内容
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                # 使用Server-Sent Events格式返回数据
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                
        # 发送结束信号
        yield f"data: {json.dumps({'finished': True}, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        # 发送错误信息
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

@app.post("/chinese-teacher")
async def chinese_teacher(request: QuestionRequest):
    """
    语文老师路由 - 专门解答语文相关问题
    """
    system_prompt = """
    你是一位经验丰富的语文老师，擅长古代文学、现代文学、语言文字知识、作文指导等。
    你的回答应该：
    1. 准确专业，引经据典
    2. 深入浅出，通俗易懂
    3. 富有文采，语言优美
    4. 注重培养学生的文学素养和语言表达能力
    5. 适当引用经典诗文来解释概念
    请用中文回答所有问题。
    """
    
    def generate():
        return qwen_max_stream(request.question, system_prompt)
    
    return StreamingResponse(
        generate(), 
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/math-teacher")
async def math_teacher(request: QuestionRequest):
    """
    数学老师路由 - 专门解答数学相关问题
    """
    system_prompt = """
    你是一位资深的数学老师，精通各个年级的数学知识，包括算术、代数、几何、统计、概率等。
    你的回答应该：
    1. 逻辑清晰，步骤详细
    2. 先给出解题思路，再展示具体步骤
    3. 适当使用数学符号和公式
    4. 注重培养学生的数学思维和解题能力
    5. 对复杂问题要分步骤讲解
    6. 必要时提供多种解法
    请用中文回答所有问题。
    """
    
    def generate():
        return qwen_max_stream(request.question, system_prompt)
    
    return StreamingResponse(
        generate(), 
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/english-teacher")
async def english_teacher(request: QuestionRequest):
    """
    英语老师路由 - 专门解答英语相关问题
    """
    system_prompt = """
    你是一位专业的英语老师，精通英语语法、词汇、阅读理解、写作、口语等各个方面。
    你的回答应该：
    1. 语法解释清晰准确
    2. 提供实用的例句和用法
    3. 注重语言的实际应用
    4. 适当进行中英文对照说明
    5. 培养学生的英语思维
    6. 提供记忆技巧和学习方法
    7. 涉及文化背景时要适当解释
    请主要用中文回答，在需要时提供英文例句和说明。
    """
    
    def generate():
        return qwen_max_stream(request.question, system_prompt)
    
    return StreamingResponse(
        generate(), 
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/")
async def root():
    """
    根路由 - 提供API信息
    """
    return {
        "message": "AI教师助手API",
        "version": "1.0.0",
        "endpoints": {
            "/chinese-teacher": "语文老师问答",
            "/math-teacher": "数学老师问答", 
            "/english-teacher": "英语老师问答"
        },
        "usage": "发送POST请求到相应端点，请求体格式: {'question': '你的问题'}"
    }

if __name__ == "__main__":
    import uvicorn
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8010, reload=False) 