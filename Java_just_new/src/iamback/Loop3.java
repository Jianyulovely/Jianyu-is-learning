package iamback;

public class Loop3 {
    public void printRes(){
        int[] nums = {12, 5, 7, 19, 3, 8};

        int max = 0;
        float avg = 0;
        int count_above_avg = 0;

        for(int i = 0; i < nums.length; i++){
            avg = avg + nums[i];
        }
        avg = avg / nums.length;

        for(int i = 0; i < nums.length; i++){
            if(nums[i] > max){
                max = nums[i];
            }
            if(nums[i] > avg){
                count_above_avg++;
            }
        }
        System.out.println("最大值为：" + max);
        System.out.println("平均值为：" + avg);
        System.out.println("大于平均值的数的个数为：" + count_above_avg);
    }
}
