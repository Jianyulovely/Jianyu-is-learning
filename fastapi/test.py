from fastapi import FastAPI
from pydantic import BaseModel

# 创建一个FastAPI实例
app = FastAPI()

# 根路由
@app.get("/")
async def root():
    """返回一个简单的欢迎信息。"""
    return {"message": "Hello World"}

# 用户页面 - 使用路径参数（动态路由）
@app.get("/user/{username}")
async def user_page(username: str):
    """根据提供的用户名返回用户信息。"""
    return f"the user's name is: {username}"

# 搜索功能 - 使用查询参数
# /search?keyword=nihaom  这个用法
@app.get("/search")
async def search(keyword: str = ""):
    """根据提供的关键词返回搜索结果。"""
    return f"用户搜索了关键词: {keyword}"

# 定义一个模型类LoginForm，用于验证登录信息
class LoginForm(BaseModel):
    username: str
    password: str

# 登录功能 - 使用POST请求体
@app.post("/login")
async def login(form_data: LoginForm):
    """验证登录信息并返回相应的响应。"""
    if form_data.username == "admin" and form_data.password == "123456":
        # 如果用户名和密码正确，则返回登录成功的响应
        token = {"status": "login", "username": form_data.username}
        return token
    else:
        return {"error": "用户名或密码错误"}

# 新增一个返回纯文本的路由
@app.get("/plaintext")
async def plaintext_endpoint():
    """返回一个简单的纯文本响应。"""
    return "这是一个纯文本响应"

# 新增一个返回JSON数据的路由
@app.get("/jsondata")
async def jsondata_endpoint():
    """返回一个简单的JSON对象。"""
    data = {"key": "value", "list": [1, 2, 3]}
    return data