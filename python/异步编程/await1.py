import asyncio
import time

async def sub_task():
    print('sub task')
    return 100

async def task():
    # 暂停当前的 task 执行
    # 等待 sub_task 执行完毕
    result = await sub_task()
    # 再执行后续代码
    print('result:', result)

def demo():
    coro = task()
    asyncio.run(coro)

if __name__ == '__main__':
    demo()