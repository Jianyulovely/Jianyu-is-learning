import numpy as np

# 读取输入
K = int(input())
data = list(map(int, input().split()))

# 构造 X 和 y
X = []
y = []

for i in range(K):
    x1 = data[i*4]
    x2 = data[i*4+1]
    x3 = data[i*4+2]
    price = data[i*4+3]
    
    X.append([1, x1, x2, x3])
    y.append(price)

X = np.array(X, dtype=float)
y = np.array(y, dtype=float)

# 正规方程求解
# @是矩阵乘法 .T求转置 np.linalg.inv()求逆矩阵  * 是逐元素乘法
w = np.linalg.inv(X.T @ X) @ X.T @ y

# 读取预测数据
N = int(input())
test_data = list(map(int, input().split()))

res = []
for i in range(N):
    x1 = test_data[i*3]
    x2 = test_data[i*3+1]
    x3 = test_data[i*3+2]
    
    pred = w[0] + w[1]*x1 + w[2]*x2 + w[3]*x3
    res.append(str(int(round(pred))))

print(" ".join(res))

# ========================================================================================
# 自己写的：
import sys
import numpy as np

K = int(input())

# 先进行接收，然后进行处理
# 这里有4K个整数
train_sapmle = list(map(int, input().split()))

N = int(input())

# 3N 个整数
test_sample = list(map(int, input().split()))
# 构造X矩阵 X = [[1, x11, x12, x13] , [1, x21, x22, x23],... ,[1, xK1, xK2, xK3]]
X = []
# 构造Y矩阵 Y = [y1, y2, ..., yk]
Y = []

for i in range(K):
    # 取固定间隔的数值
    data1 = train_sapmle[4*i]
    data2 = train_sapmle[4*i+1]
    data3 = train_sapmle[4*i+2]
    price = train_sapmle[4*i+3]

    X.append([1, data1, data2, data3])
    Y.append(price)

X = np.array(X)
Y = np.array(Y)

# 根据公式进行计算
W = np.linalg.inv(X.T @ X) @ X.T @ Y

# 这里可以发现W是一个一维数组(4,)
# print(W.shape)
Z = []
for i in range(N):
    data1 = test_sample[3*i]
    data2 = test_sample[3*i+1]
    data3 = test_sample[3*i+2]
    Z.append([1, data1, data2, data3])

Z = np.array(Z)
res = Z @ W
print(*(round(res[i]) for i in range(N)))





