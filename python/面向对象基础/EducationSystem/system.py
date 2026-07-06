from student import Student

def input_score(subject: str) -> float:
    """对于输入成绩进行异常判断"""
    while True:
        try:
            score = float(input(f"请输入{subject}成绩："))
            if 0<=score<=100:
                return score
                
        except ValueError:
            print("输入成绩不在有效区间(0-100)，请输入正确的数字！")

class EduManager:
    system_version = "1.0"
    system_name = "教务管理系统"
    def __init__(self) -> None:
        self.student_list: list[Student] = []  # 学生成绩信息列表
    

    def add_student(self):
        print("----------------添加学生成绩功能----------------")
        name = input("请输入学生姓名：")

        for stu in self.student_list:
            if name == stu.name:
                print(f"系统中已有{name}的成绩数据，只能修改或删除")
                return 
        
        # input 录入部分不可能得到None，所以可以去掉学生类中的 |None
        chinese = input_score("语文")
        math = input_score("数学")
        english = input_score("英语")

        self.student_list.append(Student(name, chinese, math, english))
        print("添加学生成绩成功！")

        return 

    def update_student(self):
        print("----------------修改学生成绩功能----------------")
        name = input("请输入学生姓名：")

        for stu in self.student_list:
            if name == stu.name:
                print(stu)
                chinese = input_score("语文")
                math = input_score("数学")
                english = input_score("英语")

                if 0<=chinese<=100 and 0<=math<=100 and 0<=english<=100:
                    stu.update_score(chinese, math, english)
                    print("修改学生成绩成功！")
                    print(stu)
                else:
                    print("输入成绩不在有效区间(0-100)")
                return
        print("系统中没有该学生成绩，无法修改！")
        return
        
        
    def del_student(self):
        print("----------------删除学生成绩功能----------------")
        name = input("请输入学生姓名：")
        for stu in self.student_list:
            if name == stu.name:
                self.student_list.remove(stu)
                print("学生成绩删除成功！")
                return 
        print("系统中没有该学生成绩，无法删除！")
        return


    def check_student(self):
        print("----------------查询学生成绩功能----------------")
        name = input("请输入学生姓名：")
        for stu in self.student_list:
            if name == stu.name:
                print(stu)
                return
        print("系统中没有该学生成绩！")

    def show_all(self):
        """展示所有学生成绩"""
        print("----------------展示学生成绩功能----------------")
        for stu in self.student_list:
            print(stu)

        return

    def run(self):
        while True:
            print("""
        ======== 教务管理系统 ========
        1. 添加学生
        2. 修改学生
        3. 删除学生
        4. 查询学生
        5. 显示所有学生
        0. 退出系统
        =============================
        """)
            menu = {
                1: self.add_student,
                2: self.update_student,
                3: self.del_student,
                4: self.check_student,
                5: self.show_all
            }
            choice = int(input("请输入要使用的功能编号："))
            if choice == 0:
                print("欢迎下次使用！")
                break
            
            sys_fun = menu.get(choice)
            if sys_fun:
                try:
                    sys_fun()
                except Exception as e:
                    print("程序出错，请重新选择操作。错误信息：", e)
            else:
                print("超出功能范围！请输入正确功能编号(1-5)")

if __name__ == "__main__":
    system = EduManager()
    while True:    
        system.add_student()