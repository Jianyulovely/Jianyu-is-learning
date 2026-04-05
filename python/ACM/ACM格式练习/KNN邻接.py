import sys
from collections import Counter

k, m, n, s = map(int, input().split())

test_feature = list(map(float, input().split()))

sample = [list(map(float, input().split())) for _ in range(m)]

def dist(a, b):
    dim = len(a)
    dis = 0
    for d in range(dim):
        dis = dis + (a[d] - b[d]) ** 2
    return dis

sample_feature = []
sample_label = []
for row in sample:
    # 处理维度不定长问题
    sample_feature.append(row[0:len(row)-1])
    sample_label.append(row[-1])


# 排序后查找原来位置的label值
# 排序怎么不乱索引？使用.index
# 将测试点与样本点进行距离计算
dis = []
for i in range(m):
    dis.append(dist(test_feature, sample_feature[i]))

# 对于原本距离列表进行排序，取最小的前k个
sort_dis = sorted(dis)
final_index =[]

# 得到K个近邻的索引，里面的顺序是按照k进行排序的，数值是索引值
for i in range(k):
    final_index.append(dis.index(sort_dis[i]))

labels = [sample_label[i] for i in final_index]
# 这里用到了Counter，如果后续忘了可以看python\collection\counter.py
counter = Counter(labels)
label, count = counter.most_common(1)[0]
print(int(label), count)






