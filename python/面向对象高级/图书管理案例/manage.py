from book import Book
from consumer import Consumer

class LibrarySystem:
    def __init__(self):
        self.books = list[Book] = []
        self.consumers = list[Consumer] = []
        self.import_data()

    def import_data(self):
        """
        导入图书和用户数据
        """
        book = Book()
        self.books.append(book)
        print("图书和用户数据导入成功！")

    def login(self) -> Consumer:
        """
        用户登录,登录成功后返回用户对象,登录失败后提示用户重新输入  
        只有成功登录后才能进行其他操作
        """
        while True:
            print("【登录】")
            user_account = input("请输入会员卡号: ")
            user_password = input("请输入密码: ")

            # 先核对用户名，然后核对密码
            for consumer in self.consumers:
                if consumer.account_number == user_account:
                    if consumer.get_password() == user_password:
                        print(f"登录成功，欢迎您，{consumer.name}!")
                        return consumer
                    else:
                        print("密码错误")
                        continue

            # 如果用户名不存在，提示用户注册
            print("用户名不存在，请先注册！")

    def borrow_book(self, consumer: Consumer):
        """
        借阅图书
        """
        
        print("【图书列表】")
        for book in self.books:
            book.show_info()
        book_number = input("请输入图书编号: ")

        for book in self.books:
            if book.number == book_number:
                consumer.borrow_book(book)

                return
        print("图书编号不存在")
        return 


    def return_book(self, consumer: Consumer):
        """
        归还图书
        """
        self.check_borrow(consumer)
        book_number = input("请输入要归还的图书编号: ")

        for book in consumer.get_borrowed_books():
            if book.number == book_number:
                consumer.return_book(book)
                return
        print("图书编号不存在")
        return 

    def check_borrow(self, consumer: Consumer):
        """
        查看当前用户已经借阅的图书列表
        """
        for book in consumer.get_borrowed_books():
            book.show_info()
        
        return 
    
    def run(self):
        """
        运行图书管理系统
        """
        consumer = self.login()

        menu = {
            "1": self.borrow_book,
            "2": self.return_book,
            "3": self.check_borrow,
        }
        
        while True:
            choice = input("请选择您的操作(1-4): ")
            if choice == "4":
                print("再见！")
                break
            
            sys_fun = menu.get(choice)
            if sys_fun:
                try:
                    sys_fun(consumer)
                except Exception as e:
                    print(f"功能执行异常，错误信息: {e}")

            else:
                print("无效的操作选择，请重新输入！")
            
            


    