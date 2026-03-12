package SwitchDemo;

import java.util.Scanner;

public class SwitchDemo2 {
    public static String WhichSeason(int month){
        switch (month) {
            case 1:
            case 2:
            case 12:
                return "现在是冬季";
                
            case 3:
            case 4:
            case 5:
                return "现在是春季";
                
            case 6:
            case 7:
            case 8:
                return "现在是夏季";
                
            case 9:
            case 10:
            case 11:
                return "现在是秋季";
                
            default:
                return "输入错误";              
        }
    }

    // switch新表达式
    public static String WhichSeason2(int month){
        String season = switch (month){
            case 1, 2, 12 -> {
                yield "现在是冬季";
            }
            case 3, 4, 5 -> {
                yield "现在是春季";
            }
            case 6, 7, 8 -> {
                yield "现在是夏季";
            }
            case 9, 10, 11 -> {
                yield "现在是秋季";
            }
            default -> {
                yield "输入错误";
            }
        };
        return season;
    }

    // 输入月份，选择对应的季节
    public static void main(String[] args) {
         
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入月份（1-12）：");
        int month = sc.nextInt();
        String season = WhichSeason(month);
        System.out.println(season);
        String season2 = WhichSeason2(month);
        System.out.println(season2);
        
    }
}
