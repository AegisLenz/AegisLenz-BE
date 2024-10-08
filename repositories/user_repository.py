from models.user_model import User

class UserRepository:
    def __init__(self):
        self.users = [
            User(id=1, name="John Doe", email="johndoe@example.com"),
            User(id=2, name="Jane Doe", email="janedoe@example.com"),
            User(id=3, name="Alice", email="alice@example.com")
        ]
        self.counter = 4  # 새로운 사용자를 추가할 때 사용할 ID

    def find_by_id(self, user_id: int):
        for user in self.users:
            if user.id == user_id:
                return user
        return None