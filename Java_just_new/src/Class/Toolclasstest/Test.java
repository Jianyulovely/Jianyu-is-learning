package Class.Toolclasstest;

public class Test {
    public static void main(String[] args) {
        int[] arr = {1, 2, 3, 4, 5};

        // 可以不用创建对象就使用类中的静态方法
        // 静态只能调用静态
        // 非静态可以调用静态和非静态
        System.out.println(ArrayUtil.printArray(arr));
        System.out.println(ArrayUtil.getAverage(arr));
    }
}
