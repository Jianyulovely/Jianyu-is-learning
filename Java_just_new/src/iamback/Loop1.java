package iamback;

public class Loop1 { 
    //用 for 循环打印 1 到 100 之间所有能被 7 整除的数。
    public void printLoop(){
        for(int i = 0; i < 100; i++){
            if (i % 7 == 0){
                System.out.println(i);
            }
        }
    }
}
