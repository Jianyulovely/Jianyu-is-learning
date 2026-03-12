package get_started;

public class Variable {
    public static void main(String[] args) {
        // 定义3个变量记录微信，支付宝，银行卡余额

        double weixinmoney = 0;
        double alipay = 10;
        double card = 20;
        
        double sum = weixinmoney + alipay + card;
        double rest = weixinmoney + 10 - 2;

        System.out.println(sum);
        System.out.println(rest);

        // 可以连续赋值
        int a, b, c, d;
        a = b = 10;
        
        c = a + b;
        d = a - b;
        System.out.println(c);
        System.out.println(d);
    }
}
