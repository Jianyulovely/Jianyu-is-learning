from typing import List, Dict, Optional, Union

def process_students(students: List[Dict[str, Union[str, int]]]) -> Optional[float]:
    # Union[str, int]表明字典的值可以是字符串也可以是整数
    """
    处理学生数据，计算平均分数
   
    参数:
        students: 学生列表，每个学生是包含'name'和'score'的字典
       
    返回:
        平均分数（浮点数），如果没有学生则返回None
    """
    if not students:
        return None
   
    total = 0
    for student in students:
        total += student['score']
   
    return total / len(students)

# 测试数据
students_data = [
    {"name": "Alice", "score": 95},
    {"name": "Bob", "score": 88},
    {"name": "Charlie", "score": 92}
]

average = process_students(students_data)
print(f"平均分: {average}")