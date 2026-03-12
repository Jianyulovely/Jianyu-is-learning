import time
import functools
def square1(x):
    return x ** 2

def print_running(f, x):
    print(f'{f.__name__} is running.')
    return f(x)


def decorator(func):
    def wrapper(*args, **kwargs):
        print(f'{func.__name__} is running.')
        result = func(*args, **kwargs)
        return result
    return wrapper

@decorator
def square(x):
    print("原函数被使用")
    return x ** 2

result = square(2)
print(result)

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f'{func.__name__} is running {end_time - start_time} seconds.')
        return result
    return wrapper

@timer
def delay(seconds) -> None:
    time.sleep(seconds)

delay(2)

# 装饰器生成器
def timer_with_threshold(threshold):
    def decorator(func):
        @functools.wraps(func)      # 复制func元数据到wrapper
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            if end_time - start_time > threshold:
                print(f'{func.__name__} took longer than {threshold} seconds.')   
            return result
        return wrapper
    return decorator

# 等价于 sleep_1()=timer_with_threshold(0.2)(sleep_1)
@timer_with_threshold(0.2)
def sleep_1() -> None:
    time.sleep(1)

sleep_1()