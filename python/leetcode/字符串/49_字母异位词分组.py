from typing import List
class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        ans = []
        vocab = []
        # 构建strs中每个单词的各自的字母表(这里注意，vocab初始空列表，不能用索引i赋值，只能append)
        for i, val in enumerate(strs):
            vocab.append([0]*26)
            for j in val:
                vocab[i][ord(j)-ord('a')] += 1

        # 比对每个单词的字母表，判断是否相同()
        for i in range(len(vocab)-1):

            flag = True
            # 先装进要判断的字符串
            ans.append(strs[i])
            for j in range(i+1, len(vocab)):
                
                if vocab[i] == vocab[j]:
                    flag = True
                    ans.append(strs[j])
                    # pop只能给定key值
                    strs.pop(j)
            # 如果没有字母异位词，则弹出一开始放进去的单词
            if flag!=True:
                ans.pop(i)
        return ans

# 使用python中字典建立映射关系

class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        ans = {}
        # 对于列表中每个单词进行处理，看看排序后是否相同
        # 然后用 sorted_word 当 key 存东西，存放的就是原本的单词，这样就能根据判断结果存放单词了
        for word in strs:
            sorted_word = ''.join(sorted(word))
            key = sorted_word

            if key not in ans:
                ans[key] = []

            ans[key].append(word)

        return list(ans.values())

# .join()的用法： '分隔符'.join(可迭代对象)
# 是“用某个字符串，把一组字符串连接起来”
words = ['a', 'e', 't']
print('-'.join(words))

# 注意，join只能拼字符串，这里输出不会是"123"，而是会报错
nums = [1, 2, 3]
''.join(nums)

nums = [1, 2, 3]
''.join(map(str, nums))

# 这里补充一个关于sorted(word)的知识：
word = "eat"
sorted(word)            # ['a', 'e', 't'] 是一个列表
''.join(sorted(word))   # "aet"
