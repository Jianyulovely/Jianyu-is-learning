package enumtest;

public class EnumTest1 {
    public static void main(String[] args) {

        //因为一个订单有6种可能的状态，在枚举中定义这6种状态
        // 待支付 待发货 待确认 待评价 已完成 已取消

        OrderState o1 = OrderState.WAIT_PAYMENT;
        System.out.println(o1.getName());

        switch(o1){
            case WAIT_PAYMENT -> System.out.println("待支付");
            case WAIT_DELIVERY -> System.out.println("待发货");
            case WAIT_CONFIRMATION -> System.out.println("待确认");
            case WAIT_EVALUATION -> System.out.println("待评价");
            case COMPLETED -> System.out.println("已完成");
            case CANCELED -> System.out.println("已取消");
        }
        
        OrderState[] o2 = OrderState.values();
        for(OrderState os : o2){
            System.out.println(os.getName());
        }

        OrderState o3 = OrderState.valueOf("WAIT_PAYMENT");
        System.out.println(o3.getName());
    }
}
