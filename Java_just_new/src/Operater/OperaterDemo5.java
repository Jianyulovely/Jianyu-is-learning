package Operater;

public class OperaterDemo5 {
    public static void main(String[] args) {
        // 实现字母的大小写转换
        // 定义变量记录大写字母
        char c = 'F';

        // 转成小写
        char cc = (char)(c + 32);
        System.out.println(cc);

        // 字符串只有拼接操作"+"
        // 有字符串参与的+就是拼接
        System.out.println(10+8+"岁"+1+2);
    }
}
