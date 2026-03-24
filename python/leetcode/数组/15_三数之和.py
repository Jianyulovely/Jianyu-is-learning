class Solution:
    def threeSum(self, nums: list[int]) -> list[list[int]]:
        # 这道题中表明位置索引互不相同，三数之和为0
        # 先将数组按照符号整理
        n_list = []
        p_list = []
        z_len = 0
        ans = []
        for num in nums:
            if num>0:
                p_list.append(num)
            elif num<0:
                n_list.append(num)
            else:
                z_len+=1
        if z_len>=3:
            ans.append([0,0,0])
        # 1正1负1 0
        if z_len>0:
            for i in n_list:
                if -i in p_list:
                    ans.append([i,-i,0])

        # 2 正 1 负        
        for i in n_list:
            for j in range(len(p_list)-1):
                for k in range(j, len(p_list)):
                    if i+p_list[j]+p_list[k]==0:
                        ans.append([i, p_list[j], p_list[k]])

        # 2 负 1 正        
        for i in p_list:
            for j in range(len(n_list)-1):
                for k in range(j, len(n_list)):
                    if i+n_list[j]+n_list[k]==0:
                        ans.append([i, n_list[j], n_list[k]])
        return set(ans)

# ans.append([0, 0, 0])这个操作本身完全没有问题，是列表嵌套列表
# 但是不能放进set中，因为list不能被哈希运算，只有tuple元组可以
# tuple 是只读的   set 才是用来收集去重元素的

# 这个超时了，复杂度可以降低
class Solution:
    def threeSum(self, nums: list[int]) -> list[list[int]]:
        # 这道题中表明位置索引互不相同，三数之和为0
        # 先将数组按照符号整理
        n_list = []
        p_list = []
        z_len = 0
        ans = set()
        # 填充过程：
        for num in nums:
            if num>0:
                p_list.append(num)
            elif num<0:
                n_list.append(num)
            else:
                z_len+=1

        # 对于整理好符号的数组进行排序，防止后续重复组合
        p_list = sorted(p_list)
        n_list = sorted(n_list)

        if z_len>=3:
            ans.add((0, 0, 0))
        # 1正1负1 0
        if z_len>0:
            for i in n_list:
                if -i in p_list:
                    ans.add((i, 0, -i))

        # 2 正 1 负        
        for i in n_list:
            for j in range(len(p_list)-1):
                for k in range(j+1, len(p_list)):
                    if i+p_list[j]+p_list[k]==0:
                        ans.add((i, p_list[j], p_list[k]))

        # 2 负 1 正        
        for i in p_list:
            for j in range(len(n_list)-1):
                for k in range(j+1, len(n_list)):
                    if i+n_list[j]+n_list[k]==0:
                        ans.add((i, n_list[j], n_list[k]))
        return [list(i) for i in ans]

# 数据结构问题：list列表用于遍历，set用于查找，set不能使用索引
# 这道题难点在于：双指针、去重操作，逻辑性极强！！想了很久debug很久理解了很久才明白
class Solution:
    def threeSum(self, nums: list[int]) -> list[list[int]]:
        nums.sort()
        ans = []
        
        for i in range(len(nums)):

            # 第一步去重
            if i>0 and nums[i]==nums[i-1]:
                continue

            # 从最小值和最大值开始，往中间收紧
            left = i + 1
            right = len(nums)- 1
            while left < right:
                s = nums[i]+nums[left]+nums[right]
                if s==0:
                    ans.append([nums[i], nums[left], nums[right]])
                    left = left+1
                    right = right-1
                    # 去重措施，这个很关键想了很长时间
                    while left < right and nums[right+1]==nums[right]:
                        right = right - 1
                    while left < right and nums[left-1]==nums[left]:
                        left = left + 1

                # 说明左边的数太小了
                elif s<0:
                    left = left + 1
                    while left < right and nums[left-1]==nums[left]:
                        left = left + 1
                else:
                    right = right - 1
                    while left < right and nums[right+1]==nums[right]:
                        right = right - 1
        
        return ans

