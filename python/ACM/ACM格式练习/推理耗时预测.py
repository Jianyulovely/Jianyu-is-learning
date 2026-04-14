from decimal import Decimal, ROUND_HALF_EVEN
# 样本数量
m = int(input())
# 迭代次数
N = int(input())
# 学习率
alpha = float(input())

data = [list(map(int, input().split())) for _ in range(m)]

# 对于特征进行归一化
def min_max(x):
    to_one = x[:]
    for i in range(3):
        col = []
        for j in range(m):
            col.append(to_one[j][i])
        min_val = min(col)
        max_val = max(col)

        if min_val==max_val:
            for j in range(m):
                to_one[j][i] = 0
        else:
            for j in range(m):
                to_one[j][i] = (to_one[j][i]-min_val) / (max_val-min_val)
        
    return to_one

def predict(X, W, B):
    P = [0]*m
    for i in range(m):
        res = 0
        for j in range(3):
            res += X[i][j] * W[j]
        P[i] = res + B
    return P

def minus(pred, label):
    dis = []
    for i in range(m):
        dis.append(pred[i] - label[i])

    return dis

def get_grad(to_one, dis):
    grad = []
    # 计算每个权重梯度
    for i in range(3):
        avg = 0
        for j in range(m):
            avg += to_one[j][i] * dis[j]
        grad.append(avg / m)
    return grad
    
def get_back(w, b, min_val, max_val):

    for i in range(3):
        if max_val[i]==min_val[i]:
            w[i] = 0
        else:
            w[i] =  w[i] / (max_val[i]-min_val[i])
    
    ans = 0
    for i in range(3):
        ans += w[i]*min_val[i]
    b = b - ans

    return w, b

# 这个逻辑经常用到，好好记一记
def point_2(x):
    # float 是用二进制保存的小数，是无限近似的
    # 而Decimal后是用十进制进行保存的，完全精确
    d = Decimal(str(x))
    # quantize 返回的是 Decimal 对象， 将结果转为字符串更明确
    return str(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN))

x = []
y = []
w = [0]*3
b = 0

for i in range(m):
    x.append(data[i][0:3])
    y.append(data[i][3])

min_val = []
max_val = []
# 获得原始数据每列 最大值 最小值
for i in range(3):
    col = []
    for j in range(m):
        col.append(x[j][i])
    min_val.append(min(col))
    max_val.append(max(col))


# 归一化在训练开始前做一次即可
to_one = min_max(x)

for i in range(N):
    # 预测的时候的x 使用的是经过归一化后的x
    pred = predict(to_one, w, b)
    # 预测值与真实值之差 的和
    dis = minus(pred, y)                # [-50, -100]
    # 梯度计算
    grad_w = get_grad(to_one, dis)

    for j in range(3):
        w[j] = w[j] - grad_w[j] * alpha

    avg = 0
    grad_b = 0
    for j in range(m):
        avg += dis[j]

    grad_b = avg / m


    b = b - alpha * grad_b


pred = predict(x, w, b)
w, b = get_back(w, b, min_val, max_val)
print(point_2(b), point_2(w[0]), point_2(w[1]), point_2(w[2]))






