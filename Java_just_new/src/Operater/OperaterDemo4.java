package Operater;

public class OperaterDemo4 {
    public static void main(String[] args) {
        // 练习1：
        byte b = 100;
        short s = 200;
        double d = 20.3;

        // byte&short转为int，再转为double
        /*
        *1. b+s->int
        *2. b+s+d int->double    
        */
        double result1 = b + s + d;
        System.out.println(result1);

        // 练习2：
        short s1 = 100;
        short s2 = 200;

        //byte result2 = s1 + s2; 不行，short先转为int
        // 300的二进制结果被截断为8位，结果为44
        byte result2 = (byte)(s1 + s2);
        System.out.println(result2);

        int result3 = s1 + s2;
        System.out.println(result3);
    }
}
