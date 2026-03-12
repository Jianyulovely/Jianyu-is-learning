import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

def thread_task(futrue):
    time.sleep(5)
    futrue.set_result(100)


async def sub_task():
    print('sub task 开始')

    # 创建 future 对象
    event_loop = asyncio.get_running_loop()
    future = event_loop.create_future()
    # 创建线程池对象
    executor = ThreadPoolExecutor()
    # 在其他线程执行任务
    event_loop.run_in_executor(executor, thread_task, future)
    # 挂起当前任务，事件循环调度其他任务执行
    result = await future

    print('sub task 结束')
    return result


async def task1():
    print('task1 开始')
    # await 协程直接进行
    result = await sub_task()
    print('task1 结束')
    return result


async def task2():
    print('task2 开始')
    await asyncio.sleep(1)
    print('task2 结束')
    return 200


async def main():
    result = await asyncio.gather(task1(), task2())
    print(result)


if __name__ == '__main__':
    time_start = time.time()
    asyncio.run(main())
    print(time.time() - time_start)
