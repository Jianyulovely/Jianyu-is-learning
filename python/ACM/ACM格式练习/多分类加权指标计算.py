from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

pred = list(map(int, input().split()))
trueY = list(map(int, input().split()))
weights = list(map(float, input().split()))

l = len(pred)
# 获得所有的标签的类别（注意：这里必须确保pred和trueY中元素都在label中，否则会出现种类不匹配情况）
labels = []
for i in trueY:
    if i not in labels:
        labels.append(i)
for i in pred:
    if i not in labels:
        labels.append(i)

labels = sorted(labels)
# print(labels)
# 保存每个类别预测结果
result = []
# 对于每一种标签种类，统计对应位置的标签内容
for label_type in labels:
    TP = 0
    FP = 0
    FN = 0
    for i in range(l):
        if label_type==trueY[i] and label_type==pred[i]:
            TP += 1
        elif label_type==trueY[i] and label_type!=pred[i]:
            FN += 1
        elif label_type!=trueY[i] and label_type==pred[i]:
            FP += 1
    result.append([TP, FP, FN])
# print(result) # [[3, 0, 1], [1, 1, 1], [1, 2, 1]]

# 三种指标
def precision(ans):
    if (ans[0] + ans[1])==0:
        return 0
    else:
        return ans[0] / (ans[0] + ans[1])

def recall(ans):
    if (ans[0] + ans[2])==0:
        return 0
    else:
        return ans[0] / (ans[0] + ans[2])

def f1_score(ans):
    p = precision(ans)
    r = recall(ans)
    if p+r==0:
        return 0
    else:
        return 2*p*r/(p+r)

mid_ans = []
for res in result:
    p = precision(res)
    r = recall(res)
    f = f1_score(res)
    mid_ans.append([p, r, f])


p = 0
r = 0
f = 0

p = sum(mid_ans[j][0]*weights[j] for j in range(len(labels)))
r = sum(mid_ans[j][1]*weights[j] for j in range(len(labels)))
f = sum(mid_ans[j][2]*weights[j] for j in range(len(labels)))

def round2(x):
    return Decimal(str(x)).quantize(Decimal('0.00'), rounding = ROUND_HALF_UP)
# 严格保留两位，相比于round不会舍弃0
# 但是format是银行家舍入，如果是0.525,则不会将5进一位
print(format(p, '.2f'), format(r, '.2f'), format(f, '.2f'))

print(round2(p), round2(r), round2(f))
# print(round(p, 2), round(r, 2), round(f, 2))























