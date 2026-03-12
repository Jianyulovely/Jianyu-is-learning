package polymorphic.Test1;

public class StudentManger {
    // 定义一个方法表示注册用户
    // 这里可以传递person以及person子类的对象
    public void register(Person p){
        // 姓名为张三同学注册成功，密码为123456
        System.out.println("姓名为" + p.getName() + "的同学注册成功，密码为" + p.getPassword()); 

        // 根据多态的用法，这里调用的是子类的work方法，它们都进行了重写
        p.work();
    }
}
