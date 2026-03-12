package Extends;

public class Test1 {
    public static void main(String[] args) {
        Zi1 z1 = new Zi1();
        Zi2 z2 = new Zi2();
        z1.eat();
        z1.drink();
        z1.study();
        
        z2.eat();
        z2.drink();
        z2.lunch();
    }
}

class Fu {
    public void eat(){
        System.out.println("父类方法：吃");
    }

    public void drink(){
        System.out.println("父类方法：喝");
    }
}

class Zi1 extends Fu{

    // this.eat(); 执行语句不能写在类中，只能放在方法内部
    public void study(){
        System.out.println("子类方法：学习");
    }
}

class Zi2 extends Fu{

    public void sleep(){
        System.out.println("子类方法：睡觉");
    }
    // this.eat(); 执行语句不能写在类中，只能放在方法内部
    public void lunch(){
        super.eat();
        super.drink();
        this.sleep();
    }

}