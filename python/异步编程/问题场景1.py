import time

def task1():
    time.sleep(5)  # 模拟一个耗时 5 秒的 I/O 操作
    return 10

def task2():
    time.sleep(3)  # 模拟一个耗时 3 秒的 I/O 操作
    return 20

def main():
    result = task1()
    print('任务1执行结果:', result)
    result = task2()
    print('任务2执行结果:', result)

if __name__ == '__main__':
    start = time.time()
    main()
    print('总耗时:', time.time() - start)