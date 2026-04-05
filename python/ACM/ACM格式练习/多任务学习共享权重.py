# ==================================================================
# 虽然这个代码不能满足题目要求，但是其中的对于输入处理方法以及ny方法的使用
# 还是很有价值的，毕竟之前我不会
import numpy as np 

# 这里是一个字符串列表
lines = input().split(';')
f_mat = []
for line in lines:
    f_mat.append(list(map(float, line.split(','))))
f_mat = np.array(f_mat)
# 用contact操作给特征矩阵添加一个列
ones = np.ones((f_mat.shape[0], 1))
f_mat = np.concatenate((ones, f_mat), axis=1)


lines = input().split(';')
l_mat = []
for line in lines:
    l_mat.append(list(map(float, line.split(','))))
l_mat = np.array(l_mat)

N = int(input())
lr = float(input())
alpha = float(input())

# W 形状：行数和x维度数一样，列数是类别数量
W = np.zeros((f_mat.shape[1], 2))
X = f_mat
L = l_mat

# 初始先算一次误差结果
Y = X @ W
dis = L - Y
MSE_ctr = sum((dis[i][0])**2 for i in range(dis.shape[0])) / dis.shape[0]
MSE_cvr = sum((dis[i][1])**2 for i in range(dis.shape[0])) / dis.shape[0]
# print(MSE_ctr, MSE_cvr)
loss = MSE_ctr + alpha * MSE_cvr

for i in range(N):
    Y = X @ W
    dis = L - Y
    MSE_ctr = sum(dis[i][0] for i in range(dis.shape[0])) / dis.shape[0]
    MSE_cvr = sum(dis[i][1] for i in range(dis.shape[0])) / dis.shape[0]
    loss = MSE_ctr + alpha * MSE_cvr
    # 更新W权重
    W = W + dis * loss * lr

print(round(loss*(10**10)))
