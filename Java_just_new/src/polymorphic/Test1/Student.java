package polymorphic.Test1;

public class Student extends Person{
    public Student(){
        super();
    }
    public Student(String name, int age, String password){
        super(name, age, password);
    }

    @Override
    public void work(){
        System.out.println(getName() + "的工作是学习");
    }
}
