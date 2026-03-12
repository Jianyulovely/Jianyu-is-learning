package enumtest;

public enum OrderState {
    // 所有枚举项默认使用public static final修饰
    // 待支付 待发货 待确认 待评价 已完成 已取消
    WAIT_PAYMENT("待支付"),
    WAIT_DELIVERY("待发货"),
    WAIT_CONFIRMATION("待确认"),
    WAIT_EVALUATION("待评价"),
    COMPLETED("已完成"),
    CANCELED("已取消");

    private String name;

    // 私有化构造方法，不可以外部创建对象
    private OrderState(String name){
        this.name = name;
    }

    public String getName(){
        return name;
    }


}
