# 解法一，注意sorted默认按照从小到大排序，可以设置reverse进行大到小排序
class Solution:
    def isMonotonic(self, nums: List[int]) -> bool:
        a = sorted(nums)
        b = sorted(nums, reverse = True)
        if a==nums or b==nums:
            return True
        else:
            return False

# 解法二运行时间更短，用两个标记遍历一次就行，逐个比较判断是否有矛盾之处
class Solution:
    def isMonotonic(self, nums: List[int]) -> bool:
        increase = True
        decrease = True
        for i in range(len(nums)-1):
            if nums[i]<nums[i+1]:
                decrease = False
            if nums[i]>nums[i+1]:
                increase = False

        return increase or decrease