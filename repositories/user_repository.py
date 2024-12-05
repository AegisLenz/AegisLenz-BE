from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from models.asset_model import UserAsset
from models.user_model import User
from database.mongodb_driver import mongodb
from common.logging import setup_logger

logger = setup_logger()


class UserRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

    async def get_user_asset(self, user_id: str, asset_type: str):
        try:
            user_asset = await self.mongodb_engine.find_one(UserAsset, {"user_id": user_id})
            if not user_asset:
                logger.error(f"No assets found for user ID '{user_id}'.")
                raise HTTPException(status_code=404, detail=f"No assets found for user ID '{user_id}'.")

            if asset_type == "EC2":
                return {"EC2": [ec2.dict() for ec2 in user_asset.asset.EC2]}
            elif asset_type == "S3_Bucket":
                return {"S3_Bucket": [bucket.dict() for bucket in user_asset.asset.S3]}
            elif asset_type == "IAMUser":
                return {"IAMUser": [iam.dict() for iam in user_asset.asset.IAM]}
            else:
                logger.error(f"Invalid asset type '{asset_type}' specified for user ID '{user_id}'.")
                raise HTTPException(status_code=400, detail=f"Invalid asset type '{asset_type}' specified. Valid types are 'EC2', 'S3_Bucket', or 'IAMUser'.")
        except Exception as e:
            logger.error(f"Unexpected error while fetching assets for user ID '{user_id}': {e}")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving assets for user ID '{user_id}'. Please try again later.")
    
    async def get_user_policies(self, user_id: str):
        try:
            user_asset = await self.mongodb_engine.find_one(
                UserAsset,
                UserAsset.user_id == user_id
            )
            if not user_asset:
                logger.error(f"No policies found for user ID '{user_id}'.")
                raise HTTPException(status_code=404, detail=f"No policies found for user ID '{user_id}'.")
            
            # 각 IAM 유저의 AttachedPolicies를 추출하여 반환
            attached_policies_by_user = {
                iam.UserName: iam.AttachedPolicies for iam in user_asset.asset.IAM
            }
            return attached_policies_by_user
        except Exception as e:
            logger.error(f"Unexpected error while fetching policies for user ID '{user_id}': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve user policies for user ID '{user_id}': {str(e)}")

    async def create_bookmark(self, user_id: str, question: str):
        try:
            user = await self.mongodb_engine.find_one(
                User,
                User.id == user_id
            )
            if not user:
                user = User(
                    id="1",
                    email="jyjyjy7418@gmail.com",
                    created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None),
                    updated_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
                )
            
            user.bookmark.append(question)
            await self.mongodb_engine.save(user)
            return {"message": f"Bookmark '{question}' successfully added for user ID '{user_id}'."}
        except Exception as e:
            logger.error(f"Unexpected error while adding bookmark for user ID '{user_id}': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add bookmark for user ID '{user_id}': {str(e)}")

    async def find_bookmark(self, user_id: str):
        try:
            user = await self.mongodb_engine.find_one(
                User,
                User.id == user_id
            )
            if not user:
                logger.error(f"User with ID '{user_id}' not found.")
                raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found")
            return user.bookmark
        except Exception as e:
            logger.error(f"Unexpected error while retrieving bookmarks for user ID '{user_id}': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve bookmarks for user ID '{user_id}': {str(e)}")

    async def delete_bookmark(self, user_id: str, question: str):
        try:
            user = await self.mongodb_engine.find_one(
                User,
                User.id == user_id
            )
            if not user:
                logger.error(f"User with ID '{user_id}' not found.")
                raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found")

            if question in user.bookmark:
                user.bookmark.remove(question)
                user.updated_at = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
                await self.mongodb_engine.save(user)
                return {"message": f"The bookmark '{question}' has been successfully deleted for user ID '{user_id}'"}
            else:
                logger.error(f"The bookmark '{question}' was not found for user ID '{user_id}'.")
                raise HTTPException(status_code=404, detail=f"The bookmark '{question}' was not found for user ID '{user_id}'")
        except Exception as e:
            logger.error(f"Unexpected error while deleting bookmark '{question}' for user ID '{user_id}': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete bookmark '{question}' for user ID '{user_id}': {str(e)}")
