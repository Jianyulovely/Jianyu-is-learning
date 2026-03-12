import asyncio
import time
import requests
import aiohttp

# 目标
# 编写一个程序，同时请求多个 API，并 并发获取结果，最后汇总输出。

# http请求由两个阶段：
# 1. 发送请求
# 2. 接收响应

# 如果只使用get，则没有读取返回数据。而在aiohttp,如果不正确处理 response，连接不会被正确释放。

async def fetch(session, url):
    print("start:", url)
    async with session.get(url) as response:
        result = await response.text()
    print("done:", url)
    return result


async def main():
    urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/2",
    "https://httpbin.org/delay/3"
    ]
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        print(len(results))


if __name__ == '__main__':
    time_start = time.time()
    asyncio.run(main())
    print(time.time() - time_start)
