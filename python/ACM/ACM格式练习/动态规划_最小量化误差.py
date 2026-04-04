import math

line1 = input().split()
N, H, Qmax = int(line1[0]), int(line1[1]), int(line1[2])

layers = []
for _ in range(N):
    weights = list(map(float, input().split()))
    layers.append(weights)

def calc_error(weights, q):
    err = 0
    scale = 2 ** q
    for w in weights:
        wq = int(w * scale)   # 注意：int()是截断，要小心负数
        wr = wq / scale
        err += abs(w - wr)
    return err

INF = float('inf')
dp = [INF] * (Qmax + 1)
dp[0] = 0

for i in range(N):
    new_dp = [INF] * (Qmax + 1)
    for j in range(Qmax + 1):
        if dp[j] == INF:
            continue
        for q in [2, 4, 8]:
            if j + q <= Qmax:
                e = calc_error(layers[i], q)
                new_dp[j + q] = min(new_dp[j + q], dp[j] + e)
    dp = new_dp

ans = min(dp[q_used] for q_used in range(N*2, Qmax+1) if dp[q_used] < INF)
print(math.floor(ans * 100))