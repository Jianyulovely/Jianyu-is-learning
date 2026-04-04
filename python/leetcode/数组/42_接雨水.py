from typing import List
class Solution:
    def trap(self, height: List[int]) -> int:
        # 暴力求解——运行超时了
        # 每个位置 i 能装的水的面积由它左右边max高度的最小值决定
        l = len(height)
        res = 0
        for i in range(1, l-1):
            left = max(height[:i])
            right = max(height[i+1:])
            # 这里防止减去一个很高的位置值，得到一个负数
            res += max(0, min(left, right) - height[i])
        return res

# =============================================================================
# 其实还可以，不是很难理解，主要是双指针的操作熟练度问题
class Solution:
    def trap(self, height: List[int]) -> int:
        # 暴力求解。每个位置 i 能装的水的面积由它左右边max高度的最小值决定
        res = 0
        left = 0
        right = len(height)-1

        # 将左右最大值“存储”起来，避免每次都遍历所有位置
        # 这里按照左右指针的位置进行遍历
        # 也就是说，左右指针的位置会有当前高度信息，然后根据左右区间最大值结果进行计算（取其中最小-当前左/右指针值）
        left_max = 0
        right_max = 0
        while left < right:
      
            left_max = max(left_max, height[left])
            right_max = max(right_max, height[right])

            if left_max < right_max:
                res += max(0, left_max - height[left])
                left += 1                
            else:
                res += max(0, right_max - height[right])
                right -=1
        return res