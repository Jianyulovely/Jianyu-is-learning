# 练习题：找“第一次重复出现”的位置
# 写一个函数：返回 第一个“重复出现的数字”的索引（第二次出现的位置）
from typing import List
nums = [3, 1, 4, 2, 5, 3, 6]
def find_first_duplicate(nums: List[int]) -> int:
    vocab = [0] * (max(nums)+1)
    for i, val in enumerate(nums):
        vocab[val] += 1
        if vocab[val]==2:
            return i
    return -1

# 值得注意的是，这里有一个新学的知识点：set
# set方法使用哈希表存储，在复杂度上只有O(1)，而find一个列表复杂度是O(n),逐个遍历
# 哈希表原理：存储数值时候算一个哈希值，代表存放位置，然后查找时候直接算一下目标哈希值，然后对应即可
def find(nums: List[int]) -> int:
    seen = set()
    for i, val in enumerate(nums):
        
        if val in seen:
            return i
        else:
            seen.add(val)
    return -1

print(find_first_duplicate(nums))