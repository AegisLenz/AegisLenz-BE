from schemas.user_schema import UserSchema
from repositories import user_repository

class UserService:
    def __init__(self, user_repository=user_repository.UserRepository()):
        self.user_repository = user_repository

    def get_user_by_id(self, user_id: int):
        return self.user_repository.find_by_id(user_id)