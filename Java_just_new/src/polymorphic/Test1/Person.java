package polymorphic.Test1;

public class Person {
    private String name;
    private int age;
    private String password;

    public Person(){
        super();
    }

    public Person(String name, int age, String password){
        super();
        this.name = name;
        this.age = age;
        this.password = password;
    }
    // 提供getter和setter方法
    public String getName(){
        return name;
    }
    public void setName(String name){
        this.name = name;
    }
    public int getAge(){
        return age;
    }
    public void setAge(int age){
        this.age = age;
    }
    public String getPassword(){
        return password;
    }
    public void setPassword(String password){
        this.password = password;
    }

    public void work(){
        System.out.println(name + "需要工作");
    }

}
