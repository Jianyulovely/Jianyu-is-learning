from pydantic import BaseModel
from typing import List

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str

class User(BaseModel):
    name: str
    address: Address

user = User(name="John Doe", address={"street": "123 Elm St", "city": "Springfield", "state": "IL", "zip_code": "62704"})
print(user)


class UserList(BaseModel):
    users: List[User]

def get_users() -> UserList:
    users_data = [
        {
            "name": "John Doe",
            "address": {
                "street": "123 Elm St",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62704"
            }
        },
        {
            "name": "Jane Doe",
            "address": {
                "street": "456 Oak St",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62704"
            }
        }
    ]
    return UserList(users=users_data)


print(get_users())
