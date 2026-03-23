while True:
    try:
        a, b = map(int, input().split())
        print(a+b)
    except:
        break

# map基本用法：map(函数, 可迭代对象)
nums = ['1', '2', '3']       #这里面都是字符
print(list(map(int, nums)))
# ↑这里说明map返回一个迭代器，必须将每次函数的结果取出来

r = [1, 2, 3]
print(list(map(lambda x: x**2, r)))