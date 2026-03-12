import asyncio
import time


async def task1():
    print('task1 开始执行')
    # await 后面的对象必须是 async def 定义的对象，而 sleep 则不是，所以会报错
    # await time.sleep(5)
    # 需要切换为 async def 版本的 sleep 函数
    await asyncio.sleep(5)
    print('task1 结束执行')
    return 10

async def task2():
    print('task2 开始执行')
    # await time.sleep(5)
    await asyncio.sleep(3)
    print('task2 结束执行')
    return 20


# 任务执行入口点
async def main():
    print('main 开始执行')
    # 获得事件循环
    event_loop = asyncio.get_running_loop()
    # 手动注册任务
    t1 = event_loop.create_task(task1())
    t2 = event_loop.create_task(task2())

    # 等待事件循环调度执行、获得 t1 任务的结果
    result = await t1
    print('任务1执行结果:', result)

    # 等待事件循环调度执行、获得 t2 任务的结果
    result = await t2
    print('任务2执行结果:', result)

    # 上面内容的简化版，一般都这么写
    result = await asyncio.gather(task1(), task2())
    print('任务1和任务2的执行结果:', result)

    print('main 结束执行')


if __name__ == '__main__':
    start = time.time()
    # 创建事件循环
    # event_loop = asyncio.get_event_loop()
    # 启动事件循环
    # event_loop.run_until_complete(main())

    # 上面两行的简化版本
    asyncio.run(main())
    print(time.time() - start)