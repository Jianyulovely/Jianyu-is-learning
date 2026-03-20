class Solution:
    def isRobotBounded(self, instructions: str) -> bool:
        # 规定一个机器人的面向角
        angle = 90
        x = 0
        y = 0
        for i in instructions:
            if i == 'L':
                angle = angle + 90
            if i == 'R':
                angle = angle - 90
            if angle >= 360:
                    angle = angle - 360
            if i == 'G':
                if angle == 0:
                    x = x + 1
                elif angle == 90:
                    y = y + 1
                elif angle == 180:
                    x = x - 1
                else:
                    y = y -1
        # 注意这里还有一个判断条件：运行完一系列操作后没回原点，但是方向变了也可以
        # 因为再来一次操作就回来了
        if (x==0 and y==0) or angle!=90 :
            return True
        else:
            return False
# =========================================================
# 上面的方法没有考虑到：在初始阶段进行转弯后，角度为负的情况
# 这里会导致 1. 在角度进行方向判断的时候出现问题
# 2. 在最后的方向判断的时候出问题
# 所以，这里应该使用对360取余数的方法得到一个"相对角度"
# =========================================================
class Solution:
    def isRobotBounded(self, instructions: str) -> bool:
        # 规定一个机器人的面向角
        angle = 90
        x = 0
        y = 0
        for i in instructions:
            if i == 'L':
                angle = angle + 90
            if i == 'R':
                angle = angle - 90
            if i == 'G':
                if angle % 360 == 0:
                    x = x + 1
                elif angle % 360 == 90:
                    y = y + 1
                elif angle % 360 == 180:
                    x = x - 1
                else:
                    y = y - 1
        # 注意这里还有一个判断条件：运行完一系列操作后没回原点，但是方向变了也可以
        # 因为再来一次操作就回来了
        if (x==0 and y==0) or angle%360 != 90 :
            return True
        else:
            return False
            