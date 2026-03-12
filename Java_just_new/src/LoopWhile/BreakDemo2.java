package LoopWhile;

import java.util.Scanner;

public class BreakDemo2 {


    // 逢7就过
    public static void Pass7(){
        for (int i = 1; i <= 100; i++){
            boolean flag = false;
            // 判断数字中是否有7
            if (i % 10 == 7 || i / 10 == 7){
                flag = true;
            }
            // 判断是否能被7整除或包含7
            if (i % 7 == 0 || flag ){
                System.out.println("过");
                continue;
            }
            System.out.println(i);           
        }
    }

    public static void GessNum(){
        // 生成一个1-100之间的随机数
        // random()返回一个double，范围为[0,1)
        int randomNum = (int)(Math.random() * 100) + 1;
        System.out.println("随机数为：" + randomNum);

        // 用户从键盘输入猜的数字
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入你猜的数字（1-100）：");
        int guessNum = sc.nextInt();

        // 猜错计数器
        int counter = 0;
        // 一直猜直到猜中
        while (guessNum != randomNum){
            System.out.println("猜错了");            
            counter = counter + 1;
            
            // 每猜错三次触发小保底
            if (counter % 3 == 0){
                System.out.println("触发小保底");
            }
            
            // 猜错十次触发大保底
            if (counter == 10){
                System.out.println("触发大保底");
                break;
            }    

            System.out.println("请重新输入你猜的数字（1-100）：");

            guessNum = sc.nextInt();
        }
        System.out.println("恭喜你猜对了");
        sc.close();
    }


    // 判断输入数字是否质数
    public static void judgePrime(){
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入一个数字：");
        int num = sc.nextInt();
        int counter = 0;
        for (int i = 2; i < Math.sqrt(num) ; i++){

            // 找到一个能整除num的数，就不是质数。余数为0，即能整除
            if (num % i == 0){
                counter = counter + 1;
                System.out.println(num + "不是质数");                
                break;
            }
        }
        if (counter == 0){
            System.out.println(num + "是质数");
        }
        sc.close();
    }

    public static void main(String[] args) {
        //judgePrime();
        //Pass7();
        GessNum();
    }
}
