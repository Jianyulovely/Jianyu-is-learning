class Solution:
    def isAnagram(self, s: str, t: str) -> bool:
        # 构建两个词表，互相对比就行
        vocab1 = [0] * 26
        vocab2 = [0] * 26
        for i in range(len(s)):
            vocab1[ord(s[i]) - ord('a')] += 1
        for i in range(len(t)):
            vocab2[ord(t[i]) - ord('a')] += 1
        
        if str(vocab1) == str(vocab2):
            return True
        else:
            return False