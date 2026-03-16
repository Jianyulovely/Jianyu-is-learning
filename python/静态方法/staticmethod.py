class MathUtils:

    @staticmethod
    def add(a, b):
        return a + b


res = MathUtils.add(3, 5)

print(res)

# 也可以通过对象调用

math_utils = MathUtils()
res = math_utils.add(3, 5)
print(res)


class User:

    @staticmethod
    def is_valid_email(email):
        return "@" in email


print(User.is_valid_email("example@example.com"))
