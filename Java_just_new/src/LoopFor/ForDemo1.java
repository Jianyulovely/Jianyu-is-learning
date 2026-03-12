package LoopFor;

public class ForDemo1 {
    public static void printNum(){
        System.out.println("正向-----------");
        for (int i = 1; i < 6; i++){
            System.out.println(i);
        }
        System.out.println("反向-----------");
        for (int i = 5; i > 0; i--){
            System.out.println(i);
        }
    }

    public static void addNum(){
        int sum = 0;
        for (int i = 1; i < 6; i++){
            sum += i;
        }
        System.out.println("1-5的和为：" + sum);
    }

    public static void addEvenNum(){
        int sum = 0;
        for (int i = 0; i < 101 ; i += 2){
            sum += i;
        }
        System.out.println("0-100的偶数和为：" + sum);
    }
    public static void main(String[] args) {
        printNum();
        addNum();
        addEvenNum();
    }
}
