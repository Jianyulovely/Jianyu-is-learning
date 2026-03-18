#========================================================================
# 不符合要求，必须在原本列表上修改
#========================================================================
class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        l = len(nums)
        res = [0] * l
        j = 0
        for i in range(l):
            if nums[i] != 0:
                res[j] = nums[i]
                j += 1
        return res

#========================================================================
class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        l = len(nums)
        j = 0
        for i in range(l):
            if nums[i] != 0:
                # 将为0的位置用非0替换
                nums[j] = nums[i]
                # 替换后指向下一个待替换的位置
                j += 1
        # 将后面的经过替换的数字置0
        for i in range(j, l):
            nums[i] = 0
            