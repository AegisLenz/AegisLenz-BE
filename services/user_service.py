from fastapi import Depends
from repositories.user_repository import UserRepository

class UserService:
    def __init__(self, user_repository: UserRepository = Depends()):
        self.user_repository = user_repository

    async def save_user(self, engine):
        return await self.user_repository.save_user(engine)