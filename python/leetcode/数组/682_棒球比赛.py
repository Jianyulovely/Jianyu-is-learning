# 这个方法将得分结果固定，但是解决不了一个问题：
# 删除上一个，将上一个置0，然后加倍得分，加倍的是0而不是有效的分数
class Solution:
    def calPoints(self, operations: List[str]) -> int:
        score = []
        # 循环遍历一次就行
        score = [0] * len(operations)
        for i in range(len(operations)):
            if operations[i] == "+":
                score[i] = score[i-1] + score[i-2]
            elif operations[i] == "D":
                score[i] = 2*score[i-1]
            elif operations[i] == "C":
                score[i-1] = 0
            else:
                score[i] = int(operations[i])
        return sum(score)

# 应该使用堆栈的方法
# 值得注意的是：在操作score数组的时候不能使用绝对位置，应该使用相对位置
# 即： score[i] X ---> score[-1] √
class Solution: 
    def calPoints(self, operations: List[str]) -> int: 
        score = [] # 循环遍历一次就行 
        for i in range(len(operations)): 
            if operations[i] == "+": 
                score.append(score[-1] + score[-2]) 
            elif operations[i] == "D": 
                score.append(2*score[-1]) 
            elif operations[i] == "C": 
                score.pop(-1) 
            else: 
                score.append(int(operations[i])) 
        return sum(score)