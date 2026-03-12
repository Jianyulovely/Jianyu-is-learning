package Array;

import java.util.Random;
import java.util.Arrays;

public class ArrayDemo5 {
    public static void main(String[] args) {
        int[] scores = {80, 90, 70, 60, 50, 70};
        System.out.println(scores[0]);
        //scores[1] = 100;
        // 打印数组地址
        System.out.println(scores);
        int[] resArr = delArray(scores, 70);
        printArray(resArr);
        System.out.println(" ");
        double[] pocket = getPocket(100.0, 5);
        printArray(pocket);
    }

    public static void printArray(int[] arr){
        for(int i = 0; i < arr.length; i++){
            System.out.print(arr[i] + " ");
        }
    }
    public static void printArray(double[] arr){
        for(int i = 0; i < arr.length; i++){
            System.out.print(arr[i] + " ");
        }
    }
    
    public static int[] delArray(int[] arr, int val){

        int index = 0;
        for(int i = 0; i < arr.length; i++){
            
            // 快慢指针，慢指针index指向待填充数组，快指针进行寻找非val元素
            // index隐含了非val元素个数
            if(arr[i] != val){
                arr[index] = arr[i];
                index++;
            }
        }

        int[] resArr = new int[index];
        for(int i = 0; i < index; i++){
            resArr[i] = arr[i];
        }

        return resArr;
    }

    public static double getSum(double[] arr){
        double sum = 0;
        for(int i = 0; i < arr.length; i++){
            sum += arr[i];
        }
        return sum;
    }

    public static double[] getPocket(int M, int N){
        double[] ratio = new double[N-1];
        double[] money = new double[N];
        double current = M;

        // 根据人数N生成n-1个随机切割位点
        for(int j=0; j<N-1; j++){
            Random r = new Random();
            double random = r.nextDouble(0.01, M);
            ratio[j] = random;
        }

        Arrays.sort(ratio);

        // 根据比率分钱
        for(int i=0; i<N; i++){

            // 分割位点 
            if (i == N-1){
                money[i] = current - getSum(money);
            }
            if (i == 0){
                money[i] = ratio[i];
            }
            if (i > 0 && i < N-1){
                money[i] = ratio[i] - getSum(money);
            }
                
        }
        return money;
    }


    // 更好的 方法，可以多看看
    public static double[] getPocket(double totalMoney, int peopleNum){
        int moneyInCents = (int) (totalMoney * 100);

        Random r = new Random();

        int moneyToDivide = moneyInCents - peopleNum;

        int[] randomPoints = new int[peopleNum - 1];

        for (int i = 0; i < peopleNum - 1; i++) {
            // 在剩余金额中随机撒点
            // 注意：nextInt(bound) 生成 0 到 bound-1
            randomPoints[i] = r.nextInt(moneyToDivide + 1); 
        }

        Arrays.sort(randomPoints);
        double[] result = new double[peopleNum];
        
        // 第一段
        int section1 = randomPoints[0];
        result[0] = (section1 + 1) / 100.0; // +1 是把保底的那1分钱加上
        
        // 中间段
        for (int i = 1; i < peopleNum - 1; i++) {
            int section = randomPoints[i] - randomPoints[i-1];
            result[i] = (section + 1) / 100.0;
        }
        
        // 最后一段
        int lastSection = moneyToDivide - randomPoints[peopleNum - 2];
        result[peopleNum - 1] = (lastSection + 1) / 100.0;

        return result;
    }
}
