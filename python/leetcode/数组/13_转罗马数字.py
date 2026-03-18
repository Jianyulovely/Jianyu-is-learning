class Solution:
    def romanToInt(self, s: str) -> int:
        # 字母和数字映射
        mapping = {"I": 1, "V": 5, "X":10, "L": 50, "C":100, "D":500, "M":1000}
        nums = [mapping[c] for c in s]

        ans = nums[-1]
        for i in range(len(nums)-1):
            # 注意，只对当前的位置计算。当前位置小于右边，则减去自己
            if nums[i]<nums[i+1]:
                ans = ans - nums[i]
            # 大于右边位置，则加自己
            else:
                ans = ans + nums[i]
        return ans