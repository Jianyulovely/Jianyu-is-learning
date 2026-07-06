
# __all__ 是一个模块级别的特殊变量，用于指定 from 模块名 import * 时会导入哪些功能（*通配了哪些功能）
__all__ = ["log_separator1", "log_separator2", "PI"]

PI = 3.14159
NAME = "Jason"

def log_separator1():
    print("-" * 30)

def log_separator2():
    print("*" * 30)

# __name__ 是python中内置变量，表示当前模块的名字。
# 如果直接运行当前模块，则__name__的值为"__main__"
# 如果当前模块被导入时，__name__的值为当前模块名称"my_fun"
print(__name__)
log_separator1()

# 这里可以编写测试当前模块功能的代码。
# 当模块被直接运行时，这些测试代码会执行；
# 当模块被其他模块导入时，这些测试代码不会执行。
if __name__ == "__main__":
    log_separator2()