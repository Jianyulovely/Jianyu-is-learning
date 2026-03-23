from typing import List
# ======================================================================
# 这个解法复杂度n2超时了
class Solution:
    def maxArea(self, height: List[int]) -> int:
        # 双指针，快指针遍历所有的整数，
        # 计算每种组合的面积，然后如果有更大的则进行替换
        # 最后返回最大面积
        max = 0
        for left in range(len(height)-1): # 如果长度9，则left取值0-7
            for right in range(left, len(height)):  
                now = min(height[right], height[left]) * (right - left)
                if now > max:
                    max = now
        return max

# 你可以这样想：
# 两个人拉绳子装水，水高度取决于矮的那个
# 想让水更多，只能换掉矮的那个，不能动高的那个
# 下面是复杂度O(n)的解法：
class Solution:
    def maxArea(self, height: List[int]) -> int:
        # 双指针，一个在左一个在右，大小取决于两者最小值
        # 计算完本次面积之后与现有的最大值进行比较，则下一次移动则移动左右两者最小值
        left = 0
        right = len(height)-1
        res = 0
        while right-left!=0:  # 这里防止两个指针相撞，其实用left<right更标准
            now = min(height[right], height[left]) * (right - left)
            res = max(now, res)
            if height[right] > height[left]:
                left = left + 1
            else:
                right = right - 1
        return res
