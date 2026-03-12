package Extends;

public class Teacher extends Person {
    // 老师特有属性：学科
    String subject;
    
    // 无参构造方法
    public Teacher(){
        super(); // 这里加不加没有影响
    }
    
    // 有参构造方法
    public Teacher(String name, int age, String subject){
        super(name, age);//先进行person的有参构造，进行了一次赋值给成员状态
        this.subject = subject;
    }
    
    // 特有行为：教书
    public void teach(){
        System.out.println(name + "正在教书");
    }
}
