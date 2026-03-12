package IfDemo;

import java.util.Scanner;

public class IfDemo2 {
    public static void main(String[] args) {
        
        int MaxBlood = 200;
        int MinBlood = 1;
        int Health = 200;

        System.out.println("请输入伤害值：");
        Scanner sc = new Scanner(System.in);
        int damage = sc.nextInt();

        // 判断伤害是否为正
        if (damage < 0){ //左括号不要单独起一行
            System.out.println("伤害值不能为负");
            return;
        }
        System.out.println("请输入治疗值：");
        int cure = sc.nextInt();
        

        // 造成伤害，生命值最少为1
        Health = Health - damage;
        if (Health < MinBlood){
            Health = MinBlood;
        }
        
        // 治疗，生命值最多为200
        Health = Health + cure;

        if (Health > MaxBlood){
            Health = MaxBlood;
        }

        System.out.println("当前血量为：" + Health);


    }
}
