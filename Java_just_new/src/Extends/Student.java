package Extends;

// 子类students具有父类person中的属性和方法
public class Student extends Person {

    // 学生特有属性： 年级
    String grade;
    
    // 无参构造方法
    public Student(){
        super();  // 首先调用父类 Person 的无参构造
    }
    
    // 有参构造方法
    public Student(String name, int age, String grade){
        super(name, age);
        this.grade = grade;
    }
    
    // 特有行为：学习
    public void study(){
        System.out.println(name + "正在学习");
    }
}
