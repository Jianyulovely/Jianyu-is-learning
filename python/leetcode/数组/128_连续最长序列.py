from typing import List

class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        nums_sorted = sorted(set(nums))
        if len(nums_sorted)==0:
            return 0
        if len(nums_sorted)==1:
            return 1

        for i in range(len(nums_sorted) - 1):
            if nums_sorted[i+1]-nums_sorted[i] != 1 :
                return i+1
            if i+2==len(nums_sorted):
                return i+2
# 这种方法复杂度不满足，而且面对[1,2,6,7,8]这样的输入，不能对比连续的个数
# 下面是符合复杂度的正解
class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        nums_set = set(nums)
        max_count = 0
        for num in nums_set:
            count = 1
            # num为向后查找的起点
            if num-1 not in nums_set:
                # 当数值连续时，计数器加一
                while num+1 in nums_set:
                    count += 1
                    num += 1
                # 解决多个连续数值的情况，在每次连续统计后，与最大情况进行比较
                max_count = max(count, max_count)
        return max_count


# set会去重，但是顺序不一定会重排！
nums = [10, 1, 100, 3]
print(set(nums))

