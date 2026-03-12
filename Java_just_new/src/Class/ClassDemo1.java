package Class;

public class ClassDemo1 {

    public static void main(String[] args) {

        Dog d = new Dog();
        d.name = "旺财";
        d.age = 3;
        d.color = "黄色";
        d.weight = 10.0;

        System.out.println("我有一个" + d.age + "岁的" + d.color + "的" + d.weight + "kg的" + d.name);

        Student s = new Student();
        s.setName("张三");
        s.setAge(18);
        s.sex = "男";
        s.setHeight(1.83);
        s.setWeight(70.0);
        
        System.out.println("大一新生：" + s.getName() + s.getAge() + "岁，" + s.getHeight() + "米高" + s.getWeight() + "kg");
        s.study();

        double newHeight = s.getHeight() + 0.2;
        double roundedHeight = Math.round(newHeight * 100.0) / 100.0;
        s.setHeight(roundedHeight);

        s.setAge(s.getAge() + 1);
        System.out.println("大二学生：" + s.getName() + s.getAge() + "岁，" + s.getHeight() + "米高" + s.getWeight() + "kg");
        
        s.setAge(s.getAge() + 1);
        double newWeight = s.getWeight() + 3.0;
        s.setWeight(newWeight);
        System.out.println("大三学生：" + s.getName() + s.getAge() + "岁，" + s.getHeight() + "米高" + s.getWeight() + "kg");
        
        s.setAge(s.getAge() + 1);
        System.out.println("大四学生：" + s.getName() + s.getAge() + "岁，" + s.getHeight() + "米高" + s.getWeight() + "kg");

        s.setAge(s.getAge() + 1);
        // 毕业以后
        System.out.println("毕业学生：" + s.getName() + s.getAge() + "岁，" + s.getHeight() + "米高" + s.getWeight() + "kg");

        // 不能使用s1.进行方法的使用，只能创建
        Student s1 = new Student();
        Student s2 = new Student("李四", 19, "男", 1.85, 75.0);
    }
}
