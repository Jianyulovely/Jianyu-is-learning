# main.py

from fastapi import FastAPI
from routes import router  # 导入路由

app = FastAPI()

# 将路由添加到应用中，并指定前缀
app.include_router(router, prefix="/items")

