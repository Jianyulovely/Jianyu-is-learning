package Array;

import java.util.Scanner;

public class ArrayDemo1 {

    public static void inputArray(int[] arr){
        Scanner sc = new Scanner(System.in);
        for (int i = 0; i < 5; i++){
            System.out.println("请输入第" + (i+1) + "个元素：");
            arr[i] = sc.nextInt();
            System.out.println("您输入的第" + (i+1) + "个元素是：" + arr[i]);
        }
        sc.close();
    }
    public static void main(String[] args) {
        // 方法内定义的变量：只能在该方法内使用；类内定义的变量：可以在整个类中使用
        
        // 数组的定义, 初始化默认为0
        int[] a = new int[10];
        // 数组的赋值
        a[0] = 100;
        a[1] = 200;
        a[2] = 300;

        int[] ageArr = new int[]{18, 19, 21};
        int[] scoreArr = new int[]{90, 80, 70};
        double[] heightArr = {1.7, 1.8, 1.9}; // 初始化数组时可以省略new int[]
        String[] nameArr = {"张三", "李四", "王五"};
        // 数组的遍历
        // 数组的属性：length
        for (int i = 0; i < nameArr.length; i++){
            System.out.println(a[i]);
            System.out.println(nameArr[i]);
            
        }
        
        int[] someValues = new int[5];
        inputArray(someValues);

    }
}
