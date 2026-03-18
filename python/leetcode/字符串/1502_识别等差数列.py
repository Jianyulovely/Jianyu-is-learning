# 不可以这样写，因为等差数列求和公式是一个小集合，满足求和公示的数列未必是等差数列
class Solution:
    def canMakeArithmeticProgression(self, arr: List[int]) -> bool:
        # 用等差数列公式验证
        min = arr[0]
        max = arr[0]
        sum = arr[0]
        for i in range(1, len(arr)):
            if arr[i]>max:
                max = arr[i]
            if arr[i]<min:
                min = arr[i]
            sum = sum + arr[i]
        if (min+max)*len(arr)/2 == sum:
            return True
        else:
            return False
# 注意，sort()这个方法
class Solution:
    def canMakeArithmeticProgression(self, arr: List[int]) -> bool:
            arr.sort()
            diff = arr[1] - arr[0]
            for i in range(1, len(arr)-1):
                if diff != arr[i+1] - arr[i]:

                    return False
            return True