package Extends;

public class Rewrite {
    public static void main(String[] args) {
        phone3 p = new phone3();
        p.call();
        p.sendMessage();
        p.playGame();
    }
}

class phone{
    // 第一代手机，功能只有打电话
    public void call(){
        System.out.println("打电话");
    }
} 

class phone2 extends phone{
    // 第二代手机，功能有打电话和发短信

    public void sendMessage(){
        System.out.println("发短信");
    }
}

class phone3 extends phone2{
    // 第三代手机，功能将打电话升级为视频通话和发短信和玩游戏

    // 注解，给java虚拟机看的
    @Override
    public void call(){
        System.out.println("视频通话");
    }
    
    public void playGame(){
        System.out.println("玩游戏");
    }
}