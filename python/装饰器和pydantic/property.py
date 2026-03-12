class Person_old:
    def __init__(self, age):
        self._age = age
    
    def get_age(self):
        return self._age


class Person:
    def __init__(self, age):
        self._age = age

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        if value < 0:
            raise ValueError("Age must be positive")
        self._age = value


p1= Person_old(20)

# 这里就没有，会直接报错：'Person_old' object has no attribute 'age'
# python不可以直接访问属性，只能通过方法访问
# print(p1.age)
print(p1.get_age())

p = Person(20)

# 这里age加了@property装饰器，从类的方法变成了类的属性
print(p.age)

# 这里age加了@age.setter装饰器，进行校验后赋值
p.age = 24
print(p.age)

p.age = -10
print(p.age)


