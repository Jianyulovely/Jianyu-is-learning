package Array;
import java.util.Scanner;


public class ArrayDemo4 {

    public static void getQualified(int[] scores){
        double total = 0;
        for (int i = 0; i < scores.length; i++){
            if (scores[i] >= 60){
                total++;
            }
        }
        double quali_rate = total / scores.length;
        System.out.println("及格人数为：" + total);
        System.out.println("及格率为：" + quali_rate);
        return;
    }

    public static void get_total_ave(int[] scores){
        double ave = 0;
        double total = 0;
        for (int i = 0; i < scores.length; i++){
            total += scores[i];
        }
        ave = total / scores.length;
        System.out.println("总分为：" + total);
        System.out.println("平均分为：" + ave);
        return;
    }

    public static void getMax(int[] scores){
        int max = 0;
        for (int i = 0; i < scores.length; i++){
            if (scores[i] > max){
                max = scores[i];
            }
        }
        System.out.println("最高成绩是：" + max);
        return;
    }

    public static void main(String[] args) {
        // 录入10个学生的成绩
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入10个学生的成绩：");
        int[] scores = new int[10];
        for (int i = 0; i < scores.length; i++){
            System.out.println("请输入第" + (i+1) + "个学生的成绩：");
            int judge = sc.nextInt();
            if (judge < 0 || judge > 100){
                System.out.println("您输入的成绩有误，请重新输入：");
                i--;
                continue;
            }
            scores[i] = judge;
        }
        getQualified(scores);
        get_total_ave(scores);
        getMax(scores);
        sc.close();
    }
}
