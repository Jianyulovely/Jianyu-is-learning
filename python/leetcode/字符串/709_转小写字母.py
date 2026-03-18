# lower()方法能够将字符串转为小写
# upper()方法能够将字符串转为大写

s = "hello"
print(s.upper())

# 在ASCII中'A'=65, 'a'=97, 相差32
# 还可以这样
# 注意右端的码为“90“而不是91。因为数量=结束值-起始值+1
class Solution:
    def toLowerCase(self, s: str) -> str:
        res = ""
        for i in s:
            # 根据ASCII中'A'=65, 'a'=97, 相差32
            if ord(i) >= 65 and ord(i) < 91:
                res = res + chr(ord(i) + 32)
            else:
                res = res + i
        return res