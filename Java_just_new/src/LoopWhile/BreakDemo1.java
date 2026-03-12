package LoopWhile;

import java.util.Scanner;

public class BreakDemo1 {
    
    public static void main(String[] args) {
         
        int MaxBlood = 200;
        int MinBlood = 1;
        int Health = 200;
        int damage = 0;
        int cure = 0;
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入伤害值：");
        // 输入伤害值为负则一直输入直到为正
        while (true){
            
            damage = sc.nextInt();
            if (damage > 0){ //左括号不要单独起一行
                break;
            }
            else{
                System.out.println("伤害值不能为负");           
            }
        }

        // 造成伤害，生命值最少为1
        Health = Health - damage;
        if (Health < MinBlood){
            Health = MinBlood;
        }

        while (true){
            System.out.println("请输入治疗值：");
            cure = sc.nextInt();
            if (cure > 0){ 
                break;
            }
            else{
                System.out.println("治疗值不能为负");           
            }
        }
        
        // 治疗，生命值最多为200
        Health = Health + cure;

        if (Health > MaxBlood){
            Health = MaxBlood;
        }

        System.out.println("当前血量为：" + Health);
        sc.close();
    }
}
