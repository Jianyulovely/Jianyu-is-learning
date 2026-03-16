from abc import ABC, abstractmethod

class Animal(ABC):
    def __init__(self, name):
        self.name = name
    def speak(self):
        pass

    # 这里的eat方法是一个抽象方法，必须在子类中实现
    @abstractmethod
    def eat(self):
        return "Eating..."

# 这里的Dog和Cat都是Animal的子类
class Dog(Animal):
    def speak(self):
        return "Woof!"

    def eat(self):
        return "Dog is Eating..."     

class Cat(Animal):
    def speak(self):
        return "Meow!"

dog1 = Dog("Buddy")
print(dog1.name)
print(dog1.speak())
print(dog1.eat())