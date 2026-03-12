import asyncio

async def task():
    print('task')

def demo():
    coro = task()
    # <class 'coroutine'>
    asyncio.run(coro)

if __name__ == '__main__':
    demo()