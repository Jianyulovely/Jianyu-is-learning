class Book:
    def __init__(self, number: str, header: str, author: str, total: int, available: int):
        self.number = number
        self.header = header
        self.author = author
        self.total = total
        self.available = available
    
    def borrow_book(self):
        """
        借阅图书
        """
        if self.available > 0:
            self.available -= 1
            return True
        else:
            print(f"图书 {self.header} 已借阅完")
            return False
    
    def return_book(self):
        """
        归还图书
        """
        self.available += 1

    def show_info(self):
        """
        显示单个图书信息
        """
        print(f"编号: {self.number}, 标题: {self.header}, 作者: {self.author}, 总数: {self.total}, 可用: {self.available}")
