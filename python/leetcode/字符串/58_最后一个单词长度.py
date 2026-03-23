# 这里使用了strip()和split()
# strip()用于删除字符串中位于开头或结尾的字符，如果不填入指定字符则删除空格

str = "我是尹健宇"
str1 = "  你好吗 "
name = str.strip("我是")
res = str1.strip()
print(name)
print(res)

# spilt()用于对字符串进行指定分隔符的切片,输出一个列表
str = "Line1-abcdef \nLine2-abc \nLine4-abcd"
print(str.split( ))       # 以空格为分隔符，包含 \n
print(str.split(' ', 1 )) # 以空格为分隔符，分隔成两个（这里面的1是指分割次数）