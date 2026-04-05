from collections import Counter
labels = [1,1,2,3,4,4]

# Counter 是一个专门用来统计词频的字典
counter = Counter(labels)
print(counter)

# 返回 [(元素, 次数)]
print(counter.most_common(1))

# most_common(k) 表示出现次数最多的前k个元素
a, b = counter.most_common(1)[0]
print(a, b)

print(counter.most_common(2))
