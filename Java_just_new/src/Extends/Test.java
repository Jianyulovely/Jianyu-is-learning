package Extends;

public class Test {
    
    public static void main(String[] args) {
        Student s = new Student();
        s.name = "张三";
        s.age = 18;
        s.grade = "三年二班";
        s.eat();
        s.study();

        System.out.println(s.name + "," + s.age + "," + s.grade);
    }
}
