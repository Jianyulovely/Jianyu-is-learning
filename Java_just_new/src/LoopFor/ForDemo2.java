package LoopFor;
import java.util.Scanner;

public class ForDemo2 {

    public static int divide3and5(int num1, int num2){
        int counter = 0;

        // 确保num1小于等于num2
        if (num1 > num2){
            int temp = num1;
            num1 = num2;
            num2 = temp;
        }
        // 查找满足条件的数字
        for (int i = num1; i <= num2; i++){
            if (i % 3 == 0 && i % 5 == 0){
                counter++;
            }
        }
        return counter;
    } 

    public static void findpattern(int place){
        int place1 = 0;
        int place2 = 1;
        int place3 = 0;

        // 后一个数是前两个数的和，轮流赋值移动窗口
        for (int i = 3; i <= place; i++){
            place3 = place1 + place2;
            place1 = place2;
            place2 = place3;
        }
        System.out.println("第" + place + "位的数字为：" + place3);
    }

    // 交错级数的和
    public static void seqSum(int place){
        int sum = 0;
        for (int i = 1; i <= place; i++){

            // 不可以在这里面随便更改i的值，否则会影响循环判断
            if (i % 2 == 0){
                sum = sum - i;
            }
            else{
                sum = sum + i;
            }
        }
        System.out.println("前" + place + "项的和为：" + sum);
    }
    public static void main(String[] args) {
        // 键盘输入两个数字
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入第一个数字：");
        int num1 = sc.nextInt();
        System.out.println("请输入第二个数字：");
        int num2 = sc.nextInt();
        int result = divide3and5(num1, num2);
        System.out.println("有" + result + "个数字同时能被3和5整除");
        System.out.println("请输入要查找的位数：");
        int place = sc.nextInt();
        findpattern(place);
        seqSum(place);
    }
}
