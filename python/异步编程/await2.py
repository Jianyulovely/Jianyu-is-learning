import asyncio

async def task02():
    print('task02')
    return 200

async def sub_task():
    print('sub_task')
    return 100

async def task01():
    print('task01')
    # 如果后面是协程，事件循环不会直接切换其他任务执行
    result = await sub_task()
    return result

async def start():
    # 在事件循环中注册两个任务 task01 和 task02
    # 并等待两个任务的执行结果
    result = await asyncio.gather(task01(), task02())
    print(result)

def demo():
    asyncio.run(start())


if __name__ == '__main__':
    demo()