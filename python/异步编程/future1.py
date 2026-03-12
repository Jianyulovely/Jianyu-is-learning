import asyncio

async def task02():
    print('task02')
    return 200

async def sub_task():
    print('sub_task')
    return 100

async def task01():
    print('task01')
    # 注意下面的代码：sleep 内部会执行 await future，此时任务会切换到任务2去执行
    await asyncio.sleep(3)
    result = await sub_task()
    return result

async def start():
    result = await asyncio.gather(task01(), task02())
    print(result)

# 先进行task1，然后await到一个future进行任务切换，切换到task2执行，等task2执行完毕，再切换回task1执行

if __name__ == '__main__':
    asyncio.run(start())