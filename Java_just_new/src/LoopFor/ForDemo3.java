package LoopFor;

public class ForDemo3 {

    public static void star(){
        for (int i = 1; i <= 5; i++){
            for (int j = 1; j <= 4; j++){
                // print是不换行的
                System.out.print("*");
            }
            System.out.println();
        }
    }

    public static void Forwardstar(){
        for (int i = 1; i <= 5; i++){
            for (int j = 1; j <= i; j++){
                // print是不换行的
                System.out.print("*");
            }
            System.out.println();
        }
    }

    public static void Backwardstar(){
        for (int i = 1; i <= 5; i++){
            for (int j = 1; j <= 6-i; j++){
                // print是不换行的
                System.out.print("*");
            }
            System.out.println();
        }
    }

    // 平行四边形
    public static void Parallelogram(){
        for (int i = 1; i <= 3; i++){
            
            for (int k = 1; k <= 3 - i; k++){
                System.out.print(" ");
            }
            for (int l = 1; l <= 6; l++){
                System.out.print("*");
            }
            System.out.println();
        }
    }


    // 梯形
    public static void Trapezoid(){
        for (int i = 1; i <= 3; i++){
            for (int k = 1; k <= 3 - i; k++){
                System.out.print(" ");
            }
            for (int l =1; l <= 2 * i + 1; l++){
                System.out.print("*");
            }
            for (int k = 1; k <= 3 - i; k++){
                System.out.print(" ");
            }
            System.out.println();
        }
    }

    // 菱形
    public static void Diamond(){
        for (int i = 1; i <= 4; i++){
            for (int k = 1; k <= 4-i; k++){
                System.out.print(" ");
            }
            for (int l = 1; l <= 2 * i - 1; l++){
                System.out.print("*");
            }
            for (int k = 1; k <= 4-i; k++){
                System.out.print(" ");
            }
            System.out.println();
        }
        for (int i = 1; i <= 3; i++){
            for (int k = 1; k <= i; k++){
                System.out.print(" ");
            }
            for (int l = 1; l <= 7 - 2 * i; l++){
                System.out.print("*");
            }
            for (int k = 1; k <= i; k++){
                System.out.print(" ");
            }
            System.out.println();
        }
    }

    public static void Mul_Table(){
        for (int i = 1; i <= 9; i++){
            for (int j = 1; j <= i; j++){
                System.out.print(j + "*" + i + "=" + i * j + " ");
            }
            System.out.println();
        }
    }
    public static void main(String[] args) {
        star();
        System.out.println();
        Forwardstar();
        System.out.println();
        Backwardstar();
        System.out.println();
        Parallelogram();
        System.out.println();
        Trapezoid();
        System.out.println();
        Diamond();
        System.out.println();
        Mul_Table();
    }
}
