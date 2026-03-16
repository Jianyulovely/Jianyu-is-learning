#========================================================================
# 一开始的答案，没有考虑输入为ababba的问题，即子串的位置问题
# 字符种类数量 ≠ 重复子串长度
#========================================================================
class Solution:
    def repeatedSubstringPattern(self, s: str) -> bool:
        if (len(s) % 2 != 0):
            return False
        vocab = [0] * 26
        for i in range(len(s)):
            vocab[ord(s[i]) - ord('a')] += 1
        # 检测词表中元素种类，长度能整除种类即可
        kinds = 0
        for i in range(26):
            if vocab[i] != 0:
                kinds += 1
        if len(s) % kinds == 0:
            return True
        else:
            return False

#========================================================================
class Solution:
    def repeatedSubstringPattern(self, s: str) -> bool:

        for i in range(1, len(s)):
            # 先保证子串长度是整数倍
            if (len(s) % i == 0):
                # 这里是python字符串乘法，子串重复n次
                if (s[:i] * (len(s)//i) == s):
                    return True
        else:
            return False