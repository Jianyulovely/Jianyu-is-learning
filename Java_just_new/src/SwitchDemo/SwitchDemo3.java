package SwitchDemo;

import java.util.Scanner;

public class SwitchDemo3 {

    public static double Calculator(String operater){
        double a = 10;
        double b = 5;

        double result = switch (operater) {
            case "+" -> {
                yield a + b;
            }
            case "-" -> {
                yield a - b;
            }
            case "*" -> {
                yield a * b;
            }
            case "/" -> {
                yield a / b;
            }
            default -> {
                yield 0;
            }
        };
        return result;
    }
    public static void main(String[] args) {

        // case选项有限个，有限使用switch而不是ifelse
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入运算符：");
        String operater = sc.next();
        double result = Calculator(operater);
        System.out.println(result);
    }
    
}
