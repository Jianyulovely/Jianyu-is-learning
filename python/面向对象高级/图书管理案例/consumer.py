from book import Book

class Consumer:
    def __init__(self, name: str, account_number: str, password: str):
        self.name = name
        self.account_number = account_number
        self.__password = password
        self.__borrowed_books = list[Book] = []
        self.quota = 3
    
    def get_borrowed_books(self) -> list[Book]:
        return self.__borrowed_books

    def borrow_book(self, book: Book):
        """
        借阅图书
        """
        # 检查用户是否超出最大借阅量
        if len(self.__borrowed_books) >= self.quota:
            print("您已超出最大借阅量,无法借阅图书！")
            return 
        
        if book.borrow_book():
            self.__borrowed_books.append(book)
            print(f"{self.name} 已成功借阅图书 {book.header}")
            
            return 

        else:
            return
    
    def return_book(self, book: Book):
        """
        归还图书
        """
        if book in self.__borrowed_books:
            self.__borrowed_books.remove(book)
            book.return_book()
            
            print(f"{self.name} 已成功归还图书 {book.header}")

        else:
            print(f"图书 {book.header} 未被借阅")


    def get_password(self) -> str:
        return self.__password
    


class VIPConsumer(Consumer):
    def __init__(self, name: str, account_number: str, password: str, v_level: int):
        super().__init__(name, account_number, password)
        self.v_level = v_level

        self.quota = 6 + v_level
