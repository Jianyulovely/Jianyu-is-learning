package Finaltest;

public class Circle {
    // 常量pi以及半径r
    private final double PI = 3.14;
    private double radius;

    public void setRadius(double radius){
        this.radius = radius;
    }

    public double getRadius(){
        return radius;
    }

    // 计算圆的面积
    public double getArea(){
        return Math.round(PI * radius * radius * 100.0) / 100.0;
    } 

    // 计算圆的周长
    public double getPerimeter(){
        return Math.round(2 * PI * radius * 100.0) / 100.0;
    }

    public Circle(){

    }

    public Circle(double radius){
        this.radius = radius;
    }
}
