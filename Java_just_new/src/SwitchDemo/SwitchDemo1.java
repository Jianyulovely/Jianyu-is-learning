package SwitchDemo;
import java.util.Scanner;

// case 穿透会输出多个结果，即对应的选项没有break关键字。可以节约代码
public class SwitchDemo1 {
    // 输入星期数，选择对应的活动
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入星期数（1-7）：");
        int week = sc.nextInt();
        switch (week) {
            case 1:
                System.out.println("今天是星期一，我要去学校");
                break;
            case 2:
                System.out.println("今天是星期二，我要去公司");
                break;
            case 3:
                System.out.println("今天是星期三，我要去学校");
                break;
            case 4:
                System.out.println("今天是星期四，我要去公司");
                break;
            case 5:
                System.out.println("今天是星期五，我要去学校");
                break;
            case 6:
                System.out.println("今天是星期六，我要去公司");
                break;
            case 7:
                System.out.println("今天是星期日，我要去学校");
                break;
            default:
                System.out.println("输入错误");
                break;
        }
    }
}
