package IfDemo;

import java.util.Scanner;

public class IfDemo3 {

    // 计算每家店的折扣结果
    public static double[] getDiscount(double cost){

        double cost1 = 0;
        double cost2 = cost;
        cost1 = cost * 0.9;
        if (cost2 >= 30){
            cost2 = cost - 10;
        }

        // new创建数组关键字，不能一次性返回多个值
        return new double[]{cost1, cost2};
    }

    // 比较两家店的折扣结果，返回更优惠的那家店
    public static String getMax(double a, double b){
        if (a > b){
            return "去饿了么合适";
        }
        else{
            return "去美团合适";
        }
    }
    public static void main(String[] args) {

       Scanner sc = new Scanner(System.in);
       System.out.println("请输入消费金额：");
       double cost = sc.nextDouble();
       if (cost < 0){
            System.out.println("消费金额不能为负");
            return;
       }

       double discounts[] = getDiscount(cost);
       double discount1 = discounts[0];
       double discount2 = discounts[1];

       String judge = getMax(discount1, discount2);
       System.out.println(judge);
    }
}
