from fastapi import Depends
from odmantic import ObjectId
from repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository = Depends()):
        self.user_repository = user_repository
    
    async def get_user_ec2_asset(self, user_id: str):
        return await self.user_repository.get_user_asset(user_id, "EC2")

    async def get_user_IAM_asset(self, user_id: str):
        return await self.user_repository.get_user_asset(user_id, "IAMUser")
    
    async def get_user_S3_asset(self, user_id: str):
        return await self.user_repository.get_user_asset(user_id, "S3_Bucket")

    async def create_bookmark(self, user_id: str, question: str):
        return await self.user_repository.create_bookmark(user_id, question)

    async def get_bookmarks(self, user_id: str) -> list:
        return await self.user_repository.find_bookmarks(user_id)

    async def delete_bookmark(self, bookmark_id: ObjectId):
        return await self.user_repository.delete_bookmark(bookmark_id)
