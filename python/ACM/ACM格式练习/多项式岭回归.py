from os import X_OK
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
M, N = map(int, input().split())

data = list(str(input()) for _ in range(N))

# 先求beta，然后根据beta结果带入y估计结果以及x=某一gap天数
# print(data)

def estimate_y(beta, x):
    return beta[0]*(x**2) + beta[1]*x + beta[2]

def get_beta(left_data, right_data, gap_day):

    len_left = len(left_data)
    len_right = len(right_data)

    # X 与 日期有关
    X_1 = list(range(gap_day-len_left, gap_day)) + list(range(gap_day+1, gap_day+len_right+1))
    X_2 = np.array(list(X_1[i] **2 for i in range(len(X_1))))
    X_1 = np.array(X_1)
    X_0 = np.array([1]*(len(X_1)))
    X = np.vstack((X_2, X_1, X_0))

    sample = left_data + right_data
    sample = list(map(float, sample))

    I = np.eye(3)
    y = np.array(sample).T
    beta = np.linalg.inv(X @ X.T + 0.1 * I) @ X @ y

    return beta

gap_days = []
# 构造训练样本
for i, val in enumerate(data):
    if 'G' in val:
        gap_days.append(i+1)

def get_train_sample(day):  # 17
    # gap_days 检索
    gap_index = gap_days.index(day)    # 1
    if gap_index==0:
        last_gap = 0
        next_gap = gap_days[gap_index+1]
    elif gap_index==len(gap_days)-1:
        last_gap = gap_days[gap_index-1]
        next_gap = len(data)+1
    else:
        last_gap = gap_days[gap_index-1]   # 2
        next_gap = gap_days[gap_index+1]   # 34
 
    # 截取数据
    left_data = data[last_gap:day-1]
    right_data = data[day:next_gap-1]
    return left_data, right_data

def round2(x):
    d = Decimal(str(x))
    return str(d.quantize(Decimal('0.01'), rounding = ROUND_HALF_UP))

res = []
for day in gap_days:
    left_data, right_data = get_train_sample(day)
    beta = get_beta(left_data, right_data, day)
    res.append(estimate_y(beta, day))

for i in range(len(res)):
    print(f"Gap_{i+1}: {round2(res[i])}")












