package Class.Static;

public class Pencilcase {
    private String brand, colour;
    private int price;
    private String[] content = {"铅笔", "橡皮", "钢笔"};

    public Pencilcase(String brand, String colour, int price){
        this.brand = brand;
        this.colour = colour;
        this.price = price;
    }

    public String getPencilcaseBrand(){
        return brand;
    }
    public void setPencilcaseBrand(String brand){
        this.brand = brand;
    }

    public String getPencilcaseColour(){
        return colour;
    }
    public void setPencilcaseColour(String colour){
        this.colour = colour;
    }

    public int getPencilcasePrice(){
        return price;
    }
    public void setPencilcasePrice(int price){
        this.price = price;
    }

    public String[] getPencilcaseContent(){
        return content;
    }

}
