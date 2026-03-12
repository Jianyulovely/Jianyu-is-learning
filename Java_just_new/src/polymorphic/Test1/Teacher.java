package polymorphic.Test1;

public class Teacher extends Person{
    public Teacher(){
        super();
    }
    public Teacher(String name, int age, String password){
        super(name, age, password);
    }
    
    @Override
    public void work(){
        System.out.println(getName() + "的工作是教学");
    }
}
