package LoopWhile;

import java.util.Scanner;

public class WhileDemo1 {

    // 计算投资获得两倍本金收益时间，复利方法
    public static int investTime(double money){
        int time = 0;
        double rate = 0.017;
        double expectmoney = money * 2;
        while (money < expectmoney){
            money = money * (1 + rate);
            time++;
        }
        return time;
    }

    // 折纸超过山峰
    public static int foldTime(){
        int time = 0;
        double fold = 0.1;
        int height = 8848860;
        while (fold < height){
            fold = fold * 2 ;
            time++;
        }
        return time;
    }

    // 数位之和
    public static int digitSum(int num){
        int sum = 0;

        // 取绝对值
        if (num < 0){
            num = -num;
        }

        // 再求每个位数上的数字，不断对十取余求具体的位数值
        // 先求输入数的位数，不断除以十，每除一次计数器加一       
        while (num > 0){
            int digitNum = num % 10;
            sum = sum + digitNum;
            num = num / 10;
        }
        return sum;

    }
    public static void main(String[] args) {
        double money = 100000;
        int time = investTime(money);
        System.out.println("需要" + time + "年才能翻倍");
        int foldtime = foldTime();
        System.out.println("需要" + foldtime + "次折纸才能超过山峰");
        Scanner sc = new Scanner(System.in);
        System.out.println("数位之和的输入整数：");
        int num = sc.nextInt();
        int sum = digitSum(num);
        System.out.println("数位之和为：" + sum);
    }
}
