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


# =================================================================================
# 这一版其实还是错的，但是实现了权重共享，只不过参数更新方式有问题
import numpy as np 

# 这里是一个字符串列表
lines = input().split(';')
f_mat = []
for line in lines:
    f_mat.append(list(map(float, line.split(','))))
f_mat = np.array(f_mat)


lines = input().split(';')
l_mat = []
for line in lines:
    l_mat.append(list(map(float, line.split(','))))
l_mat = np.array(l_mat)

N = int(input())
lr = float(input())
alpha = float(input())

# W 形状：行数和x维度数一样，列数是1（因为权重共享）
W = np.zeros((f_mat.shape[1], 1))
X = f_mat
L = l_mat
b_ctr = 0
b_cvr = 0

# 初始先算一次误差结果(利用numpy的广播机制，直接加常数就行)
Y_ctr = X @ W + b_ctr  
Y_cvr = X @ W + b_cvr

MSE_ctr = sum((L[i][0] - Y_ctr[i][0])**2 for i in range(Y_ctr.shape[0])) / Y_ctr.shape[0]
MSE_cvr = sum((L[i][1] - Y_cvr[i][0])**2 for i in range(Y_cvr.shape[0])) / Y_cvr.shape[0]

# print(MSE_ctr, MSE_cvr)
loss = MSE_ctr + alpha * MSE_cvr
W = W + loss * lr
b_ctr = b_ctr + loss * lr
b_cvr = b_cvr + loss * lr

if N != 0:
    for j in range(1, N):
        Y_ctr = X @ W + b_ctr  
        Y_cvr = X @ W + b_cvr

        MSE_ctr = sum((L[i][0] - Y_ctr[i][0])**2 for i in range(Y_ctr.shape[0])) / Y_ctr.shape[0]
        MSE_cvr = sum((L[i][1] - Y_cvr[i][0])**2 for i in range(Y_cvr.shape[0])) / Y_cvr.shape[0]

        loss = MSE_ctr + alpha * MSE_cvr
        # 更新W权重
        W = W + loss * lr
        b_ctr = b_ctr + loss * lr
        b_cvr = b_cvr + loss * lr

print(round(loss*(10**10)))




# ============================================================================================
# 这一版基本正确了
import numpy as np 
from decimal import Decimal, ROUND_HALF_UP  
# 这里是一个字符串列表
lines = input().split(';')
f_mat = []
for line in lines:
    f_mat.append(list(map(float, line.split(','))))
f_mat = np.array(f_mat)


lines = input().split(';')
l_mat = []
for line in lines:
    l_mat.append(list(map(float, line.split(','))))
l_mat = np.array(l_mat)

N = int(input())
lr = float(input())
alpha = float(input())

# W 形状：行数和x维度数一样，列数是1（因为权重共享）
W = np.zeros((f_mat.shape[1], 1))
X = f_mat
L = l_mat
b_ctr = 0
b_cvr = 0

n = L.shape[0]

# 训练过程：
for _ in range(N):
    Y_ctr = X @ W + b_ctr
    Y_cvr = X @ W + b_cvr

    MSE_ctr = np.sum((L[:, [0]] - Y_ctr)**2) / n
    grad_ctr = (2 / n) * X.T @ (Y_ctr - L[:, [0]])                      # 估计值减真实值
    grad_ctrb = (2 / n) * np.sum((Y_ctr - L[:, [0]]))

    MSE_cvr = np.sum((L[:, [1]] - Y_cvr)**2) / n
    grad_cvr = (2 / n) * X.T @ (Y_cvr - L[:, [1]])
    grad_cvrb = (2 / n) * np.sum((Y_cvr - L[:, [1]]))

    loss = MSE_ctr + alpha * MSE_cvr
    W = W - (grad_ctr + alpha * grad_cvr) * lr
    b_ctr = b_ctr - grad_ctrb * lr
    b_cvr = b_cvr - alpha * grad_cvrb * lr


# 最终参数重新计算一次联合损失：
Y_ctr = X @ W + b_ctr  
Y_cvr = X @ W + b_cvr
MSE_ctr = np.sum((L[:, [0]] - Y_ctr)**2) / n
MSE_cvr = np.sum((L[:, [1]] - Y_cvr)**2) / n
loss = MSE_ctr + alpha * MSE_cvr

# Decimal 用于高精度浮点数 .quantize进行四舍五入，Decimal('1')表示保留到整数位 ROUND_HALF_UP标注四舍五入
res = Decimal(str(loss * 1e10)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
print(int(res))






