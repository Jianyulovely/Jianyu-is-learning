"""
第4章：异步处理与中间件支持
演示异步路由处理、中间件的使用和并发处理
"""

import asyncio
import time
import logging
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="第4章：异步处理与中间件支持")


# =============================================================================
# 1. 中间件演示
# =============================================================================


@app.get("/ping")
async def ping():
    return {"message": "pong"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.perf_counter()
    
    # 记录请求信息
    logger.info(f"请求开始: {request.method} {request.url}")
    
    # 调用下一个处理器
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.perf_counter() - start_time
    
    # 添加自定义响应头
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Custom-Header"] = "FastAPI-Learning"
    
    # 记录响应信息
    logger.info(f"请求完成: {request.method} {request.url} - {response.status_code} - {process_time:.4f}s")
    
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """安全头中间件"""
    response = await call_next(request)
    
    # 添加安全相关的响应头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """简单的限流中间件示例"""
    client_ip = request.client.host
    
    # 这里应该使用 Redis 等外部存储，这里用内存字典演示
    if not hasattr(app.state, "request_counts"):
        app.state.request_counts = {}
    
    current_time = int(time.time())
    window_start = current_time - 60  # 1分钟窗口
    
    # 清理过期记录
    if client_ip in app.state.request_counts:
        app.state.request_counts[client_ip] = [
            timestamp for timestamp in app.state.request_counts[client_ip]
            if timestamp > window_start
        ]
    else:
        app.state.request_counts[client_ip] = []
    
    # 检查请求频率（每分钟最多100个请求）
    if len(app.state.request_counts[client_ip]) >= 100:
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试"
        )
    
    # 记录当前请求
    app.state.request_counts[client_ip].append(current_time)
    
    response = await call_next(request)
    return response


# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加 Gzip 压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)


# =============================================================================
# 2. 异步路由处理演示
# =============================================================================

@app.get("/")
async def root():
    """异步根路径"""
    return {"message": "欢迎来到异步处理与中间件演示！"}


@app.get("/sync-heavy")
def sync_heavy_operation():
    """同步CPU密集型操作"""
    start = time.perf_counter()
    
    # 模拟CPU密集型计算
    result = sum(i * i for i in range(1000000))
    
    duration = time.perf_counter() - start
    return {
        "type": "同步操作",
        "result": result,
        "duration": f"{duration:.4f}秒",
        "note": "此操作会阻塞线程"
    }


@app.get("/async-io")
async def async_io_operation():
    """异步I/O操作"""
    start = time.perf_counter()
    
    # 模拟异步I/O操作（如数据库查询、HTTP请求等）
    await asyncio.sleep(2)  # 模拟2秒的I/O等待
    
    duration = time.perf_counter() - start
    return {
        "type": "异步I/O操作",
        "duration": f"{duration:.4f}秒",
        "note": "此操作不会阻塞其他请求"
    }


@app.get("/concurrent-demo")
async def concurrent_demo():
    """并发处理演示"""
    start = time.perf_counter()
    
    # 并发执行多个异步任务
    tasks = [
        fetch_data_async("数据源1", 1),
        fetch_data_async("数据源2", 1.5),
        fetch_data_async("数据源3", 0.5),
    ]
    
    results = await asyncio.gather(*tasks)
    
    duration = time.perf_counter() - start
    return {
        "type": "并发处理",
        "results": results,
        "total_duration": f"{duration:.4f}秒",
        "note": "三个任务并发执行，总时间约等于最长任务的时间"
    }


@app.get("/sequential-demo")
async def sequential_demo():
    """同步顺序处理演示"""
    start = time.perf_counter()
    
    # 顺序执行同步任务
    results = [
        fetch_data_sync("数据源1", 1),
        fetch_data_sync("数据源2", 1.5),
        fetch_data_sync("数据源3", 0.5),
    ]
    
    duration = time.perf_counter() - start
    return {
        "type": "同步顺序处理",
        "results": results,
        "total_duration": f"{duration:.4f}秒",
        "note": "三个任务顺序执行，总时间等于所有任务时间的总和"
    }


@app.get("/mixed-demo")
async def mixed_demo():
    """混合处理演示 - 异步中调用同步"""
    start = time.perf_counter()
    
    # 在异步函数中顺序调用异步任务（没有并发）
    result1 = await fetch_data_async("异步数据源1", 1)
    result2 = await fetch_data_async("异步数据源2", 1.5)
    result3 = await fetch_data_async("异步数据源3", 0.5)
    
    results = [result1, result2, result3]
    
    duration = time.perf_counter() - start
    return {
        "type": "异步函数顺序执行",
        "results": results,
        "total_duration": f"{duration:.4f}秒",
        "note": "虽然使用异步函数，但没有并发，总时间仍是所有任务时间的总和"
    }


@app.get("/performance-comparison")
async def performance_comparison():
    """性能对比演示"""
    # 测试并发异步
    start_concurrent = time.perf_counter()
    tasks = [
        fetch_data_async("异步源1", 1),
        fetch_data_async("异步源2", 1.5),
        fetch_data_async("异步源3", 0.5),
    ]
    await asyncio.gather(*tasks)
    concurrent_duration = time.perf_counter() - start_concurrent
    
    # 测试同步顺序
    start_sync = time.perf_counter()
    fetch_data_sync("同步源1", 1)
    fetch_data_sync("同步源2", 1.5)
    fetch_data_sync("同步源3", 0.5)
    sync_duration = time.perf_counter() - start_sync
    
    # 测试异步顺序
    start_async_seq = time.perf_counter()
    await fetch_data_async("异步顺序源1", 1)
    await fetch_data_async("异步顺序源2", 1.5)
    await fetch_data_async("异步顺序源3", 0.5)
    async_seq_duration = time.perf_counter() - start_async_seq
    
    return {
        "性能对比": {
            "并发异步执行": {
                "duration": f"{concurrent_duration:.4f}秒",
                "description": "多个异步任务并发执行"
            },
            "同步顺序执行": {
                "duration": f"{sync_duration:.4f}秒", 
                "description": "多个同步任务顺序执行"
            },
            "异步顺序执行": {
                "duration": f"{async_seq_duration:.4f}秒",
                "description": "多个异步任务顺序执行（未并发）"
            }
        },
        "结论": {
            "并发异步": "最快，时间约等于最长任务的执行时间",
            "同步/异步顺序": "较慢，时间等于所有任务时间的总和",
            "性能提升": f"{sync_duration/concurrent_duration:.2f}倍"
        }
    }


async def fetch_data_async(source: str, delay: float):
    """模拟异步数据获取"""
    await asyncio.sleep(delay)
    return {
        "source": source,
        "data": f"来自{source}的数据",
        "delay": f"{delay}秒",
        "type": "异步"
    }


def fetch_data_sync(source: str, delay: float):
    """模拟同步数据获取"""
    time.sleep(delay)  # 使用 time.sleep 而不是 asyncio.sleep
    return {
        "source": source,
        "data": f"来自{source}的数据",
        "delay": f"{delay}秒",
        "type": "同步"
    }





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True) 