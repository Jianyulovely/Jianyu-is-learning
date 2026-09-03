"""
第3章：数据模型与验证
演示 Pydantic 模型的使用、数据校验和响应模型
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

app = FastAPI(title="第3章：数据模型与验证")


# =============================================================================
# 1. 基础 Pydantic 模型
# =============================================================================

class User(BaseModel):
    """用户基础模型"""
    username: str
    email: str
    age: Optional[int] = None
    is_active: bool = True


@app.post("/users/basic")
async def create_user_basic(user: User):
    """基础用户创建，演示自动数据校验"""
    return {
        "message": "用户创建成功",
        "user": user,
        "created_at": datetime.now()
    }


# =============================================================================
# 2. 使用 Field 进行字段验证
# =============================================================================

class Product(BaseModel):
    """商品模型，使用 Field 进行详细验证"""
    name: str = Field(..., min_length=1, max_length=100, description="商品名称")
    description: Optional[str] = Field(None, max_length=500, description="商品描述")
    price: float = Field(..., gt=0, le=1000000, description="商品价格，必须大于0")
    discount: Optional[float] = Field(None, ge=0, le=100, description="折扣百分比")
    tags: List[str] = Field(default_factory=list, description="商品标签")
    in_stock: bool = Field(True, description="是否有库存")


@app.post("/products/")
async def create_product(product: Product):
    """创建商品，演示字段验证"""
    final_price = product.price
    if product.discount:
        final_price = product.price * (1 - product.discount / 100)
    
    return {
        "message": "商品创建成功",
        "product": product,
        "final_price": final_price
    }


# =============================================================================
# 3. 自定义验证器
# =============================================================================

class Book(BaseModel):
    """图书模型，包含自定义验证器"""
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    pages: int = Field(..., gt=0, description="页数必须大于0")
    isbn: str = Field(..., pattern=r'^\d{10}(\d{3})?$', description="ISBN格式：10位或13位数字")
    published_year: int = Field(..., ge=1000, le=2024)
    
    @validator('author')
    def validate_author(cls, v):
        """验证作者名不能包含数字"""
        if any(char.isdigit() for char in v):
            raise ValueError('作者姓名不能包含数字')
        return v.strip().title()  # 去除空格并转为标题格式
    
    @validator('title')
    def validate_title(cls, v):
        """验证标题不能全为大写"""
        if v.isupper() and len(v) > 5:
            raise ValueError('标题不应全为大写字母')
        return v.strip()
    
    @validator('published_year')
    def validate_published_year(cls, v):
        """验证出版年份合理性"""
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f'出版年份不能超过当前年份 {current_year}')
        return v


@app.post("/books/")
async def create_book(book: Book):
    """创建图书，演示自定义验证器"""
    return {
        "message": "图书创建成功",
        "book": book
    }


# =============================================================================
# 4. 嵌套模型
# =============================================================================

class Address(BaseModel):
    """地址模型"""
    street: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    postal_code: str = Field(..., pattern=r'^\d{6}$', description="6位邮政编码")
    country: str = Field(default="中国")


class CustomerStatus(str, Enum):
    """客户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Customer(BaseModel):
    """客户模型，包含嵌套的地址模型"""
    name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = Field(None, pattern=r'^1[3-9]\d{9}$', description="中国手机号格式")
    address: Address
    status: CustomerStatus = CustomerStatus.ACTIVE
    join_date: datetime = Field(default_factory=datetime.now)
    
    @validator('email')
    def validate_email(cls, v):
        """验证邮箱不能是临时邮箱域名"""
        temp_domains = ['temp-mail.org', '10minutemail.com', 'guerrillamail.com']
        domain = v.split('@')[1].lower()
        if domain in temp_domains:
            raise ValueError('不允许使用临时邮箱地址')
        return v.lower()


@app.post("/customers/")
async def create_customer(customer: Customer):
    """创建客户，演示嵌套模型"""
    return {
        "message": "客户创建成功",
        "customer": customer
    }


# =============================================================================
# 5. 响应模型过滤
# =============================================================================

class UserCreate(BaseModel):
    """用户创建请求模型"""
    username: str = Field(..., min_length=3, max_length=20)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)


class UserResponse(BaseModel):
    """用户响应模型，不包含密码"""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True


# 模拟用户数据库
fake_users_db = []
user_id_counter = 1


@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """创建用户，响应中自动过滤密码字段"""
    global user_id_counter
    
    # 检查用户名是否已存在
    if any(u['username'] == user.username for u in fake_users_db):
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 模拟创建用户（实际应用中会保存到数据库）
    new_user = {
        "id": user_id_counter,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "password": user.password,  # 实际应用中会哈希处理
        "is_active": True,
        "created_at": datetime.now()
    }
    
    fake_users_db.append(new_user)
    user_id_counter += 1
    
    # 直接返回包含密码的字典，但 response_model 会自动过滤
    return new_user


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """获取用户信息，响应模型自动过滤敏感字段"""
    user = next((u for u in fake_users_db if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return user


# =============================================================================
# 6. 列表和复杂数据结构
# =============================================================================

class OrderItem(BaseModel):
    """订单项模型"""
    product_id: int = Field(..., gt=0)
    product_name: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0, le=100)
    unit_price: float = Field(..., gt=0)
    
    @property
    def total_price(self) -> float:
        """计算小计"""
        return self.quantity * self.unit_price


class Order(BaseModel):
    """订单模型"""
    customer_id: int = Field(..., gt=0)
    items: List[OrderItem] = Field(..., min_items=1, max_items=50)
    discount_rate: float = Field(0, ge=0, le=50)
    notes: Optional[str] = Field(None, max_length=500)
    
    @validator('items')
    def validate_items(cls, v):
        """验证订单项不能重复"""
        product_ids = [item.product_id for item in v]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError('订单中不能包含重复的商品')
        return v
    
    @property
    def subtotal(self) -> float:
        """计算小计"""
        return sum(item.total_price for item in self.items)
    
    @property
    def total_amount(self) -> float:
        """计算总金额（含折扣）"""
        subtotal = self.subtotal
        discount = subtotal * (self.discount_rate / 100)
        return subtotal - discount


@app.post("/orders/")
async def create_order(order: Order):
    """创建订单，演示复杂数据结构验证"""
    return {
        "message": "订单创建成功",
        "order": order,
        "summary": {
            "item_count": len(order.items),
            "subtotal": order.subtotal,
            "discount": order.subtotal * (order.discount_rate / 100),
            "total_amount": order.total_amount
        }
    }


# =============================================================================
# 7. 数据校验错误处理演示
# =============================================================================

@app.get("/validation-demo")
async def validation_demo():
    """返回各种验证示例的说明"""
    return {
        "message": "数据验证演示接口",
        "examples": {
            "basic_user": {
                "url": "/users/basic",
                "method": "POST",
                "valid_data": {
                    "username": "john_doe",
                    "email": "john@example.com",
                    "age": 25
                },
                "invalid_data": {
                    "username": "",  # 会导致验证失败
                    "email": "invalid-email",  # 会导致验证失败
                    "age": -5  # 虽然没有显式验证，但通常年龄不应为负
                }
            },
            "product": {
                "url": "/products/",
                "method": "POST",
                "valid_data": {
                    "name": "iPhone 15",
                    "description": "最新款iPhone",
                    "price": 7999.99,
                    "discount": 10,
                    "tags": ["手机", "苹果", "电子产品"]
                },
                "invalid_data": {
                    "name": "",  # 长度不符合要求
                    "price": -100,  # 价格不能为负
                    "discount": 150  # 折扣不能超过100%
                }
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True) 