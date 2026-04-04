import sys

# 输入
eps, min_samples, x = map(float, input().split())
min_samples = int(min_samples)
x = int(x)
points = [list(map(float, input().split())) for _ in range(x)]

# 距离判断
def dist(p1, p2):
    return sum((p1[d] - p2[d]) ** 2 for d in range(len(p1))) <= eps**2

# 找邻居
def region_query(i):
    neighbors = []
    for j in range(x):
        if dist(points[i], points[j]):
            neighbors.append(j)
    return neighbors

visited = [False] * x
labels = [-1] * x   # -1 = 未分类/噪声
cluster_id = 0

# 跳过已访问的点，不够核心就先标噪声，够核心就开新簇。
for i in range(x):
    if visited[i]:
        continue

    visited[i] = True
    neighbors = region_query(i)

    # 不是核心点 → 暂时噪声
    if len(neighbors) < min_samples:
        labels[i] = -1
        continue

    # 新建簇
    cluster_id += 1
    labels[i] = cluster_id

    # BFS 扩展
    queue = neighbors[:]
    while queue:
        j = queue.pop(0)

        if not visited[j]:
            visited[j] = True
            new_neighbors = region_query(j)

            if len(new_neighbors) >= min_samples:
                for nb in new_neighbors:
                    if not visited[nb]:      # ← 加这个判断
                        queue.append(nb)

        if labels[j] == -1:
            labels[j] = cluster_id

# 统计
clusters = cluster_id
noise = sum(1 for l in labels if l == -1)

print(clusters, noise)