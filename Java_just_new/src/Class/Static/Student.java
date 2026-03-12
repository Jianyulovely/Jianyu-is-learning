package Class.Static;

public class Student {
    private String studentName;
    private int studentAge;
    private static String mentor; // 老师名字，为一个班学生共享的变量

    // 构造方法
    public Student(){

    }

    // 有参构造方法
    public Student(String studentName, int studentAge, String mentor){
        this.studentName = studentName;
        this.studentAge = studentAge;
        
        // 静态变量 mentor 赋值时，需要使用类名调用
        Student.mentor = mentor;
    }

    public String getStudentName(){
        return studentName;
    }
    
    public void setStudentName(String studentName){
        this.studentName = studentName;
    }
    public int getStudentAge(){
        return studentAge;
    }

    public void setStudentAge(int studentAge){
        this.studentAge = studentAge;
    }
    
    public String getMentor(){
        return mentor;
    }
    
    public static void setMentor(String mentor){
        Student.mentor = mentor;
    }
    
}
