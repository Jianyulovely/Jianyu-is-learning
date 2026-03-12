package polymorphic.Test1;

public class Test1 {
    public static void main(String[] args) {
        Student stu = new Student("张三", 18, "123456");
        StudentManger sm = new StudentManger();
        sm.register(stu);

        Teacher tea = new Teacher("李四", 30, "4444444");
        sm.register(tea);
    }
}
