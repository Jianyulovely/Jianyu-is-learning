package Array;
import java.util.Scanner;

public class ArrayDemo3 {


    // 求数组最大值和最小值
    public static int[] getMax(int[] arr){
        int max = arr[0];
        int min = arr[0];
        for (int i = 0; i < arr.length; i++){
            if (arr[i] > max){
                max = arr[i];
            }
            if (arr[i] < min){
                min = arr[i];
            }
        }
        return new int[]{max, min};
    }

    public static double getAve(int[] arr1, int[] arr2){
        double ave = 0;
        int total = 0;
        for (int i = 0; i < arr1.length; i++){
            total += arr1[i];
        }
        for (int i = 0; i < arr2.length; i++){
            total = total - arr2[i];
        }
        ave = total / (arr1.length - 2);
        return ave;
    }
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入五个评委的打分：");
        int[] scores = new int[5];
        for (int i = 0; i < scores.length; i++){
            System.out.println("请输入第" + (i+1) + "个评委的打分：");
            scores[i] = sc.nextInt();
        }
        double ave = getAve(scores, getMax(scores));
        System.out.println("该选手的最终得分是：" + ave);
    }
}
