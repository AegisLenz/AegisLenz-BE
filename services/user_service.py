from fastapi import Depends
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
