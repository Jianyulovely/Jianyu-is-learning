package polymorphic.Test1;

public class Admin extends Person{
    public Admin(){
        super();
    }
    public Admin(String name, int age, String password){
        super(name, age, password);
    }

    @Override
    public void work(){
        System.out.println(getName() + "的工作是管理web");
    }
}
