package Class.Static;
import java.util.Arrays; 

public class Class_one{
    public static void main(String[] args) {

        // 静态变量被当前类所有的对象共享，属于类，优先于对象存在  
        // 调用方式：类名.静态变量名。对象创建的时候也产生对应的静态区
        // 对象使用完后，静态区不会被销毁。虚拟机关闭时才会销毁静态区
        Student stu1 = new Student("Jack", 12, "Mr. Smith");
        Student stu2 = new Student("Sam", 13, "Mr. Smith");
        System.out.println(stu1.getMentor());
        System.out.println(stu2.getMentor());
        Student.setMentor("Mr. Jefferson");
        System.out.println(stu1.getMentor());
        System.out.println(stu2.getMentor());

        Pencilcase pc1 = new Pencilcase("得力", "黄色", 100);
        System.out.println(pc1.getPencilcaseBrand());
        System.out.println(pc1.getPencilcaseColour());
        System.out.println(pc1.getPencilcasePrice());
        System.out.println(Arrays.toString(pc1.getPencilcaseContent()));
    }
}