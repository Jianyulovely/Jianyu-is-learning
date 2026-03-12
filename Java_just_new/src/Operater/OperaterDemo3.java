package Operater;

import java.util.Scanner;
public class OperaterDemo3 {
    public static void main(String[] args) {
        // 
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入秒数：");
        int sec = sc.nextInt();
        // 获取小时数
        int hour = sec / 3600;
        System.out.println("小时数为：" + hour);

        // 获取分钟数
        int min = (sec - hour * 3600) / 60;
        System.out.println("分钟数为：" + min);

        // 获取秒数
        int sec2 = sec - hour * 3600 - min * 60;
        System.out.println("秒数为：" + sec2);
        
        System.out.println("时间为：" + hour + "时" + min + "分" + sec2 + "秒");
    }
}
