package Cal_BMI;

import java.util.Scanner;

public class Cal_BMI {
    
    public static double CalBMI(double weight, double height){
        return weight / (height * height);
    }
    public static String EvalBMI(double BMI){
        if (BMI < 18.5){
            return "身体状态：过轻，健康风险：部分增加";
        }
        else if (BMI < 24){
            return "身体状态：正常，健康风险：正常";
        }
        else if (BMI < 27){
            return "身体状态：偏胖，健康风险：增加";
        }
        else if (BMI < 30){
            return "身体状态：肥胖，健康风险：中度增加";
        }
        else{
            return "身体状态：严重肥胖，健康风险：严重增加";
        }
    }

    public static double CalMaxWeight(double height){
        return 24 * height * height;
    }
    public static void main(String[] args) {
        // 定义3个变量记录体重，身高
        // 键盘输入体重和身高
        Scanner sc = new Scanner(System.in);
        System.out.println("请输入体重（kg）：");
        double weight = sc.nextDouble();
        System.out.println("请输入身高（m）：");
        double height = sc.nextDouble();
        if (weight <= 0 || height <= 0){
            System.out.println("输入错误");
            return;
        }

        double BMI = CalBMI(weight, height);

        String Eval_result = EvalBMI(BMI);
        System.out.println(Eval_result);

        // 计算我当前的身高在标准BMI下的最高体重
        // 标准BMI下，体重为24kg
        double maxWeight = CalMaxWeight(height);
        System.out.println("在标准BMI下，身高为" + height + "m的人，最高体重为" + maxWeight + "kg");
    }
}
