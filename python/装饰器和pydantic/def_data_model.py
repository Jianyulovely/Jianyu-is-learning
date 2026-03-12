from pydantic import BaseModel
from typing import List
import json

# 继承了BaseModel
class EmployeeModel(BaseModel):
    name: str
    age: int
    department: str
    salary: int
    habits: List[str]


employee = EmployeeModel(
    name="张三",
    age=30,
    department="销售",
    salary=5000,
    habits=["运动", "阅读"]
)

print(employee)

try:
    employee = EmployeeModel(
        name="张三",
        age=30,
        department="销售",
        salary='jaja',
        habits=["运动", "阅读"]
    )
except ValueError as e:
    print(e)

json_data = '{"name": "Bar", "age": "19", "department": "开发", "salary": "1000", "habits": []}'

# 解析JSON字符串为Python字典
data = json.loads(json_data)

employee = EmployeeModel(**data)
print(employee)
