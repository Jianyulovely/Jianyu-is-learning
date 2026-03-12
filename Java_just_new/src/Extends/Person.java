package Extends;

public class Person {
    String name;
    int age;

    public Person(){
        
    }

    // 有参构造方法
    public Person(String name, int age){
        this.name = name;
        this.age = age;
    }

    public void eat(){
        System.out.println(name + "正在吃东西");
    }

}
