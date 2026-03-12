package Class;

public class Student {
    // 属性
    private String name;

    // 防止错误的年龄值
    // 私有成员变量都要写对应的get和set 方法
    private int age;
    String sex;
    private double height;
    private double weight;

    public void setName(String name){
        this.name = name;
    }

    public String getName(){
        return name;
    }

    public void setHeight(double height){
        this.height = height;
    }
    
    public double getHeight(){
        return height;
    }

    public void setAge(int age){
        if (age > 0 && age < 120) {
            // 赋值给成员变量使用this
            this.age = age;
        }
        else{// 默认初始化值0
            System.out.println("年龄输入错误");
        }
    }
    
    public int getAge(){
        return age;
    }

    public void setWeight(double weight){
        this.weight = weight;
    }
    
    public double getWeight(){
        return weight;
    }

    // 行为，不加static
    public void study(){
        System.out.println("学生:" + name + "在学习");
    }

    public void eat(){
        System.out.println(age + "岁的" + "学生：" + name + "，在吃东西");
    }

    public void sleep(){
        System.out.println("学生在睡觉");
    }


    // 如果没有定义构造的方法，系统给出一个默认的无参构造方法
    // 如果有了定义的构造方法，系统就不会再给出默认的无参构造方法
    // 构造方法
    public Student(){
        System.out.println("空参构造方法");
    }

    // 有参构造方法
    public Student(String name, int age, String sex, double height, double weight){
        this.name = name;
        this.age = age;
        this.sex = sex;
        this.height = height;
        this.weight = weight;
        System.out.println("全参构造方法");
    }

}
