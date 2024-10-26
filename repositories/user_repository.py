from models.user_model import User

class UserRepository:
    def __init__(self):
        self.user = User(name="John Doe", age=30, email="johndoe@example.com")  # 테스트 유저 데이터

    async def save_user(self, engine):
        new_user = await engine.save(self.user)
        return new_user