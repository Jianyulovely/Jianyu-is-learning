package Finaltest;

public class Finaltest {
    public static void main(String[] args) {
        // 定义一个常量
        // 赋值后无法再修改
        final int NUMBER = 10;

        // 可以使用常量
        System.out.println(NUMBER);

        // NUMBER = 20;

        // 基本数据类型：byte short int long float double boolean char
        // 变量里面记录的是真实的数据
        // 引用数据类型： 数组 类 接口
        // 记录的是内存地址
        // 因此final修饰哪个变量，变量里面的内容就不能再变
        final Student stu1 = new Student();
        stu1.name = "Jack";
        stu1.age = 12;

        // 类中的属性是可以改变的，但是不能改变引用地址——stu1
        stu1.name = "Sam";
        stu1.age = 13;

        Circle c1 = new Circle(5.0);
        
        System.out.println(c1.getArea());
        System.out.println(c1.getPerimeter());

        // 保留n位小数：Math.round(a * 10^n) / 10^n
        // 括号中先乘1000，表示先将小数点右移三位，round取整后再左移三位，正好保留三位小数
        double a = 1.454;
        System.out.println(Math.round(a * 1000.0) / 1000.0);
    }
}
