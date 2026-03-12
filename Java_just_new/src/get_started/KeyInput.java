package get_started;
import java.util.Scanner;



public class KeyInput {
    public static void main(String[] args) {
        
        Scanner sc = new Scanner(System.in);
        int num = sc.nextInt();
        System.out.println(num);
        
        double num2 = sc.nextDouble();
        System.out.println(num2);
        
        System.out.println(num + num2);
        String str = sc.next();
        System.out.println(str);
    }
}
