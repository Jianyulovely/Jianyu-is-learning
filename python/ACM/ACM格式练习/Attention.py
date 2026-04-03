# 获得矩阵的行数和列数
A = [
    [1,2,3],
    [4,5,6]
]

col = len(A[0]) # 第一个元素的长度就是列数
row = len(A)    # 外层 list 的长度 = 行数

import math

# 输入
n, m, h = map(int, input().split())

# 1️⃣ 构造 X（n×m 全1）
X = [[1.0 for _ in range(m)] for _ in range(n)]

# 2️⃣ 构造 W（m×h 上三角1）
def build_W():
    W = [[0.0 for _ in range(h)] for _ in range(m)]
    for i in range(m):
        for j in range(h):
            if i <= j:   # 上三角
                W[i][j] = 1.0
    return W

W1 = build_W()
W2 = build_W()
W3 = build_W()

# 3️⃣ 矩阵乘法函数
def matmul(A, B):
    rows = len(A)
    cols = len(B[0])
    mid = len(B)
    C = [[0.0 for _ in range(cols)] for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            for k in range(mid):
                C[i][j] += A[i][k] * B[k][j]
    return C

# 4️⃣ 转置
def transpose(A):
    return list(map(list, zip(*A)))

# 5️⃣ 计算 Q, K, V
Q = matmul(X, W1)
K = matmul(X, W2)
V = matmul(X, W3)

# 6️⃣ 计算 S = Q·K^T / sqrt(h)
KT = transpose(K)
S = matmul(Q, KT)

for i in range(n):
    for j in range(n):
        S[i][j] /= math.sqrt(h)

# 7️⃣ softmax（题目版：除以行和）
for i in range(n):
    row_sum = sum(S[i])
    for j in range(n):
        S[i][j] /= row_sum

# 8️⃣ Y = softmax(S) · V
Y = matmul(S, V)

# 9️⃣ 求所有元素之和
total = 0
for i in range(n):
    for j in range(h):
        total += Y[i][j]

# 四舍五入输出
print(round(total))


#==============================================================================
# 自己写一遍，在矩阵乘法部分踩坑，在矩阵转置部分还是有点糊涂。
import sys
import math

n, m , h = map(int, input().split())

# 定义矩阵乘法运算
def matmul(A, B):
    col_A = len(A[0])
    row_A = len(A) 
    col_B = len(B[0])
    row_B = len(B)

    C = [[0]*col_B for _ in range(row_A)]

    if col_A != row_B:
        raise ValueError(f"{A} 与 {B} 形状不匹配，不能乘法！")
    else:
        for i in range(row_A):
            for j in range(col_B):
                for k in range(col_A):
                    C[i][j] += A[i][k]*B[k][j]

        return C

# 定义softmax函数
def softmax(R):
    r = [[0]*len(R[0]) for _ in range(len(R))]
    for i in range(len(R)):
        sum_row = sum(R[i])
        for j in range(len(R[0])):
            r[i][j] = R[i][j] / sum_row
    return r

# 定义生成上三角矩阵
def uptramat(m, h):
    A = [[0]*h for _ in range(m)]
    for i in range(m):
        for j in range(h):
            if i<=j:
                A[i][j]=1 
    return A

# 定义矩阵转置操作
def transpose(A):
    return list(map(list, zip(*A)))

X = [[1]*m for _ in range(n)]
W1 = uptramat(m, h)
W2 = uptramat(m, h)
W3 = uptramat(m, h)

Q = matmul(X, W1)
K = matmul(X, W2)
V = matmul(X, W3)

S = matmul(Q, transpose(K))

for i in range(len(S)):
    for j in range(len(S[0])):
        S[i][j] = S[i][j] / math.sqrt(h)

Y = matmul(softmax(S), V)
res = 0

for row in Y:
    res += sum(row)

print(round(res))



