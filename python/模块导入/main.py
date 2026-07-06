from my_fun import *

from utils.my_var import PI

# 导入模块的目的是使用其中的函数，因此主要用于导入预定义好的函数，但是模块中可能会有其他的代码行
# 导入 my_fun 时，模块顶层代码会执行，因此 print(__name__) 和
# log_separator1() 会运行一次；由于 __name__ 不等于 "__main__"，
# if __name__ == "__main__": 中的代码不会执行。
log_separator1()

print(PI)