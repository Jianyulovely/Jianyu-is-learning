class Student:
    def __init__(
        self, 
        name: str, 
        chinese_score: float, 
        math_socre: float, 
        english_socre: float
    ) -> None:
        self.name = name
        self.chinese = chinese_score
        self.math = math_socre
        self.english = english_socre
    
    def __str__(self):
        total = self.chinese + self.math + self.english
        return f"姓名：{self.name} | 语文：{self.chinese} | 数学：{self.math} | 英语：{self.english} | 总分：{total}"

    
    def update_score(
        self,
        chinese_score: float | None = None, 
        math_socre: float | None = None, 
        english_socre: float | None = None
    ) -> None:
        """
        根据关键字参数进行成绩修改，可以根据输入的关键字对于指定成绩进行修改（不用修改的时None）
        """
        if chinese_score is not None:
            self.chinese = chinese_score
        if math_socre is not None:
            self.math = math_socre
        if english_socre is not None:
            self.english = english_socre


if __name__ == "__main__":
    s1 = Student("Jack", 120, 130, 125)
    print(s1)
    s1.update_score(math_socre=122)
    print(s1)