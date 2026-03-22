x = 8

# if和elif是串行关系，这几个根据顺序进行判断，如果满足一个，则执行其中一个
# 语句，然后就不再判断后面的了
if x > 5:
    print("A")
elif x > 3:
    print("B")
elif x > 1:
    print("C")


# if之间是并列关系，两个都会进行判断
if x > 5:
    print("A")

if x > 3:
    print("B")