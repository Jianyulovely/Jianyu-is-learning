# 这里Animal是一个普通类
class Animal:
    def __init__(self, name):
        self.name = name
    def speak(self):
        pass
    def eat(self):
        return "Eating..."

# 这里的Dog和Cat都是Animal的子类
class Dog(Animal):
    def speak(self):
        return "Woof!"       

class Cat(Animal):
    def speak(self):
        return "Meow!"

dog1 = Dog("Buddy")
print(dog1.name)
print(dog1.speak())
print(dog1.eat())