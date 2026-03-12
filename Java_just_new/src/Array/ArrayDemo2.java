package Array;

import java.util.Scanner;
import java.util.Random;

public class ArrayDemo2 {
    public static void checkArray(){
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入要查找的数据：");
        int target_num = sc.nextInt();
        int[] arr = {33, 5, 22, 44, 55, 33};
        for (int i = 0; i < arr.length; i++){
            if (arr[i] == target_num){
                System.out.println("您要查找的数据" + target_num + "在数组中的索引为：" + i);
                return;
            }
        }
        System.out.println("您要查找的数据不在数组中");
        sc.close();
    }

    public static void checkMax(){
        int[] arr = {33, 5, 22, 44, 55};
        int max = 0;
        for (int i = 0; i < arr.length; i++){
            if (arr[i] > max){
                max = arr[i];
            }
        }
        System.out.println("数组中的最大值是：" + max);
    }
        
    public static void disorderArray(){
        int[] arr = {8, 6, 3, 4, 5, 2, 7, 1, 9, 10};
        Random r = new Random();
        
        for (int i = 0; i < arr.length; i++){
            int temp = arr[i];
            // 生成一个随机数，范围在0到arr.length-1之间
            int randomIndex = r.nextInt(0, arr.length); // 随机数范围[0, arr.length)

            //交换
            arr[i] = arr[randomIndex];
            arr[randomIndex] = temp;
        }
        // 打印 disorderArray 数组
        for (int i = 0; i < arr.length; i++){
            System.out.print(arr[i] + " ");
        }
    }

    public static void getArray(){
        int[] arr = new int[10];
        Random r = new Random();
        for (int i = 0; i < arr.length; i++){
            // 随机赋值
            arr[i] = r.nextInt(1, 100);
            // 检查是否重复，若重复则本次赋值无效
            for (int j = 0; j < i; j++){
                if (arr[i] == arr[j]){
                    i = i - 1;
                    break;
                }
            }
        }
        // 打印 getArray 数组
        for (int i = 0; i < arr.length; i++){
            System.out.print(arr[i] + " ");
        }
        // 也可以引入一个中间变量存放随机数，找一个flag，判断是否重复，如果flag为true，则数组赋值，并且i++
    }

    // 删除重复元素，使用快慢指针
    public static void delArray(){
        int[] arr = {1,1,2,2,2,2,3,3,3,3,6,7,7,9,9,9};
        int j = 0;
        // i用于寻找不重复的数字；j用于记录
        for (int i = 0; i < arr.length; i++){           
            if (arr[i] != arr[j]){
                // 找到不重复的了，用j存储
                j = j + 1;
                arr[j] = arr[i];
            }
        }

        System.out.println("删除重复元素后的数组为：");
        for (int i = 0; i <= j; i++){
            System.out.print(arr[i] + " ");
        }
    }


    public static void main(String[] args) {
        //checkArray();
        checkMax();
        disorderArray();
        getArray();
        delArray();
    }
}
