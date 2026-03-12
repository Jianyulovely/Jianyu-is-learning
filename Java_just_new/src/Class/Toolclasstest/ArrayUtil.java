package Class.Toolclasstest;

public class ArrayUtil {
    // 私有化构造方法，工具类中所有方法都是静态的
    // 数组遍历

    public static String printArray(int[] arr){
        String result = "[";
        for(int i=0; i<arr.length; i++){
            // 打印格式加入左右方括号
            if(i == arr.length - 1){
                result = result + arr[i] + "]";
            }else{
                result = result + arr[i] + ", ";
            }
        }
        return result;
    }

    public static double getAverage(int[] arr){
        int sum = 0;
        for(int i = 0; i < arr.length; i++){
            sum += arr[i];
        }
        // 小细节
        double average = sum * 1.0 / arr.length;
        System.out.println("数组的平均值为：" + average);
        return average;
    }

    private ArrayUtil(){
        // 私有化构造方法，防止外部创建对象
    }
}
