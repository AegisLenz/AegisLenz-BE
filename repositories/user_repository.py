from models.user_model import User

class UserRepository:
    def __init__(self):
        self.users = [
            User(name="John Doe", age=30, email="johndoe@example.com"),
            User(name="Jane Doe", age=25, email="janedoe@example.com")
        ]

    def find_by_id(self, user_id: int):
        for user in self.users:
            if user.id == user_id:
                return user
        return None