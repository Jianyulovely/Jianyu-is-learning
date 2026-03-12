package Operater;

import java.util.Scanner;

public class OperaterDemo8 {
    public static void main(String[] args) {
        // 输入一个数，判断是否为偶数
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入一个数：");
        int num = sc.nextInt();

        // 短路与可以提升效率，相比于单个与，如果第一个不成立那么不进行下一个判断
        boolean result = num >= 0 && num <=10;
        System.out.println(result);

        // 三元运算符判断两数较大值
        // 关系表达式 ？ 表达式1 ： 表达式2
        // 如果关系表达式成立，那么返回表达式1，否则返回表达式2
        System.out.println("请输入两个数：");
        int num1 = sc.nextInt();
        int num2 = sc.nextInt();
        int max = num1 > num2 ? num1 : num2;
        System.out.println("较大的数为：" + max);
    }
}
