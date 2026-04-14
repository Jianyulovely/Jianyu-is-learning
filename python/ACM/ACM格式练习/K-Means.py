import sys

# 读取输入
K = int(input())   # 聚类中心的个数
# 初始聚类中心的三个特征值（中心三维坐标位置）
centers = [list(map(float, input().split())) for _ in range(K)]

T = int(input())   # 迭代次数
m = int(input())   # 数据点的个数

# 一个数据点的三个特征值（数据点三维坐标位置）
points = [list(map(float, input().split())) for _ in range(m)]


# 欧氏距离（平方）
def dist(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


# KMeans 迭代
for _ in range(T):
    clusters = [[] for _ in range(K)]

    # 1. 分配
    for p in points:
        min_idx = 0
        min_dist = float('inf')
        # 寻找与每个点距离最短的类中心点，进行划分
        for i in range(K):
            d = dist(p, centers[i])
            if d < min_dist:
                min_dist = d
                min_idx = i

        # 每个点比较完后进行划分
        clusters[min_idx].append(p)

    # 2. 更新中心
    new_centers = []
    for i in range(K):
        if not clusters[i]:
            # 空簇：保持原中心
            new_centers.append(centers[i])
        else:
            # 新的簇中心点是算术平均值
            x = sum(p[0] for p in clusters[i]) / len(clusters[i])
            y = sum(p[1] for p in clusters[i]) / len(clusters[i])
            z = sum(p[2] for p in clusters[i]) / len(clusters[i])
            new_centers.append([x, y, z])

    centers = new_centers


# 输出结果
for c in centers:
    print(f"{c[0]:.2f} {c[1]:.2f} {c[2]:.2f}")


# ================================================================================================
# 自己写的版本，还是踩了很多坑
import sys

# 聚类中心个数
K = int(input())

# 初始聚类中心的三维坐标
centers = [list(map(float, input().split())) for _ in range(K)]

I = int(input())
m = int(input())

# 数据点的三维坐标
points = [list(map(float, input().split())) for _ in range(m)]

def dist(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2


for _ in range(I):
    # 一个嵌套列表，保存每个簇中的数据点结果
    cluster = [[] for _ in range(K)]
    min_idx = 0
    for p in points:
        min_dist = float('inf')
        for i in range(K):
            d = dist(p, centers[i])
            if d < min_dist:
                min_dist = d
                min_idx = i
        cluster[min_idx].append(p)
    

    new_center = []
    for i in range(K):
        # 处理空簇问题，将原本中心点进行填入
        if len(cluster[i]) == 0:
            new_center.append(centers[i])
        else:
            # 计算每组点的三维平均值
            x = sum(p[0] for p in cluster[i]) / len(cluster[i])
            y = sum(p[1] for p in cluster[i]) / len(cluster[i])
            z = sum(p[2] for p in cluster[i]) / len(cluster[i])
            new_center.append([x, y, z])

    centers = new_center

for c in centers:
    print(f"{c[0]:.2f} {c[1]:.2f} {c[2]:.2f}")

# ========================================================================================
# 4.14又做了一次，空簇处理和小数保留忘了 
from decimal import Decimal, ROUND_HALF_UP
K = int(input())
center = [list(map(int, input().split())) for _ in range(K)]
N = int(input())
m = int(input())
position = [list(map(int, input().split())) for _ in range(m)]

def dist(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2

def get_center(a):
    length = len(a)
    x = 0
    y = 0
    z = 0
    for i in range(length):
        x += a[i][0]
        y += a[i][1]
        z += a[i][2]
    return [x / length, y / length, z / length]


def round_2(x):
    d = Decimal(str(x))
    return str(d.quantize(Decimal('0.01'), rounding = ROUND_HALF_UP))

def show(x):
    dim = len(x)
    for i in range(dim):
        print(*(round_2(x[i][j]) for j in range(3)))

for _ in range(N):
    cluster = [[] for _ in range(K)] 
    # 数据点分配到距离最近的聚类中心所在的组
    for i in range(m):
        dis = []
        for j in range(K):
            dis.append(dist(position[i], center[j]))
        min_index = dis.index(min(dis))
        cluster[min_index].append(position[i])
    
    # 对每个组重新计算中心点
    for i in range(K):
        if len(cluster[i]) != 0:
            center[i] = get_center(cluster[i])
    
show(center)

    
    

            

