from pydantic import BaseModel, field_validator, ValidationError
from typing import ClassVar, List

class UserModel(BaseModel):
    name: str
    age: int
    hobbies: List[str]
    MIN_AGE: ClassVar[int] = 18    


    @field_validator('name')
    def name_must_contain_space(cls, v):  # 这里面cls是类本身
        if ' ' not in v:
            raise ValueError('must contain a space')
        return v.title()

    @field_validator('age')
    def age_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('must be a positive integer')
        return v
    
    @field_validator('age')
    def must_be_adult(cls, v):
        if v < cls.MIN_AGE:
            raise ValueError(f'must be at least {cls.MIN_AGE} years old')
        return v
    
    @field_validator('hobbies', mode='after')
    def hobbies_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('hobby cannot be empty')
        return v

try:
    user = UserModel(name="john doe", age=19, hobbies=[])
except ValidationError as e:
    print(e)
