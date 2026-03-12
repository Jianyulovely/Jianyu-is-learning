package Operater;

import java.util.Scanner;
public class OperaterDemo2 {
    public static void main(String[] args) {
        // 输入一个三位数，拆分为个位十位百位
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入一个三位数：");
        int num = sc.nextInt();
        int ge = num % 10;
        System.out.println("个位数为：" + ge);
        int shi = num / 10 % 10;
        System.out.println("十位数为：" + shi);
        int bai = num / 100 % 10;
        System.out.println("百位数为：" + bai);
    }
}
