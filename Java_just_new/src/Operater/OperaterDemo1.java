package Operater;

public class OperaterDemo1 {
    public static void main(String[] args) {
        // 整数计算
        int a = 10;
        int b = 3;
        
        
        System.out.println(a+b);
        System.out.println(a-b);
        System.out.println(a*b);
        // 整数相除，结果为整数
        System.out.println(a/b);
        System.out.println(a%b);

        System.out.println("------------------");
        // 小数计算，结果有可能不精确
        double c = 1.1;
        double d = 1.01;
        System.out.println(c+d);
        System.out.println(c-d);
        System.out.println(c*d);
        System.out.println(c/d);
        System.out.println(c%d);
    }
}
