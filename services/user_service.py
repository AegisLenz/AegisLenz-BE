from fastapi import Depends
from odmantic import ObjectId
from repositories.user_repository import UserRepository
from schemas.user_schema import GetAllBookmarkResponseSchema, BookmarkSchema
from common.logging import setup_logger

logger = setup_logger()


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

    async def get_all_bookmark(self, user_id: str) -> GetAllBookmarkResponseSchema:
        find_bookmarks = await self.user_repository.find_all_bookmark(user_id)
        if not find_bookmarks:
            logger.warning(f"No bookmarks found for user_id={user_id}")
            return GetAllBookmarkResponseSchema(bookmarks=[])

        bookmarks = [
            BookmarkSchema(bookmark_id=bookmark.id, question=bookmark.question)
            for bookmark in find_bookmarks
        ]
        return GetAllBookmarkResponseSchema(bookmarks=bookmarks)

    async def delete_bookmark(self, bookmark_id: ObjectId):
        return await self.user_repository.delete_bookmark(bookmark_id)

    async def login(self, user_name: str, user_password: str):
        return await self.user_repository.login(user_name, user_password)
    
    async def create_account(self, user_request: dict):
        return await self.user_repository.create_account(user_request)