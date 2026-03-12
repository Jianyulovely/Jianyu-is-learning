package Operater;
import java.util.Scanner;



public class OperaterDemo6 {
    public static void main(String[] args) {
        // 比较输入两个数的大小
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入第一个人身高：");
        double a = sc.nextDouble();
        System.out.println("请输入第二个人身高：");
        double b = sc.nextDouble();
        if(a > b){
            System.out.println("第一个人身高更高");
        }else if(a < b){
            System.out.println("第二个人身高更高");
        }else{
            System.out.println("两个人身高相同");
        }

        // 输入一个三位数，看是否能被三整除
        System.out.println("请输入一个三位数：");
        int num = sc.nextInt();
        int ge = num % 10;
        int shi = num / 10 % 10;
        int bai = num / 100;
        int sum = ge + shi + bai;
        if(sum % 3 == 0){
            System.out.println("这个数能被三整除");
        }else{
            System.out.println("这个数不能被三整除");
        }
    }
}
