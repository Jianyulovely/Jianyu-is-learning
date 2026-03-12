package Operater;
import java.util.Scanner;

public class OperaterDemo7 {
    public static void main(String[] args) {
        // 输入一个数，判断是否为偶数
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入一个数：");
        int num = sc.nextInt();

        // 短路与可以提升效率，相比于单个与，如果第一个不成立那么不进行下一个判断
        boolean result = num >= 0 && num <=10;
        System.out.println(result);

        // 输入一个四位整数
        System.out.println("请输入一个四位整数：");
        int num2 = sc.nextInt();
        // 取每一位的具体值
        int ge = num2 % 10;
        int shi = num2 / 10 % 10;
        int bai = num2 / 100 % 10;
        int qian = num2 / 1000;
        // 判断是否为回文数
        boolean result2 = qian == ge && shi == bai;
        System.out.println(result2);
    }
}
