from fastapi import HTTPException
from odmantic import ObjectId
from datetime import datetime, timedelta, timezone
from models.asset_model import UserAsset
from models.user_model import User, Bookmark
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
                logger.info(user_asset.asset.EC2)
                return {"EC2": [ec2 for ec2 in user_asset.asset.EC2]}
            elif asset_type == "S3_Bucket":
                return {"S3_Bucket": [bucket.dict() for bucket in user_asset.asset.S3]}
            elif asset_type == "IAMUser":
                return {"IAMUser": [iam.dict() for iam in user_asset.asset.IAM]}
            else:
                logger.error(f"Invalid asset type '{asset_type}' specified for user ID '{user_id}'.")
                raise HTTPException(status_code=400, detail=f"Invalid asset type '{asset_type}' specified. Valid types are 'EC2', 'S3_Bucket', or 'IAMUser'.")
        except Exception as e:
            logger.error(f"Error retrieving assets for user ID '{user_id}', Asset Type: '{asset_type}', Error: {e}")
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
            logger.error(f"Error retrieving policies for user ID '{user_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve user policies for user ID '{user_id}': {str(e)}")


    async def create_bookmark(self, user_id: str, question: str):
        try:
            user = await self.mongodb_engine.find_one(
                User,
                User.id == user_id
            )
            if not user:
                user = User(
                    id=user_id,
                    email="jyjyjy7418@gmail.com",
                    created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None),
                    updated_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
                )
                await self.mongodb_engine.save(user)
            
            bookmark = Bookmark(
                question=question,
                user_id=user_id
            )
            await self.mongodb_engine.save(bookmark)
            return {"message": f"Bookmark '{question}' successfully added for user ID '{user_id}'."}
        except Exception as e:
            logger.error(f"Error adding bookmark. User ID: '{user_id}', Question: '{question}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add bookmark for user ID '{user_id}': {str(e)}")

    async def find_all_bookmark(self, user_id: str):
        try:
            bookmarks = await self.mongodb_engine.find(
                Bookmark,
                Bookmark.user_id == user_id
            )
            return bookmarks
        except Exception as e:
            logger.error(f"Error retrieving bookmarks for user ID '{user_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve bookmarks for user ID '{user_id}': {str(e)}")

    async def delete_bookmark(self, bookmark_id: ObjectId):
        try:
            bookmark = await self.mongodb_engine.find_one(
                Bookmark,
                Bookmark.id == ObjectId(bookmark_id)
            )
            if not bookmark:
                raise HTTPException(status_code=404, detail=f"Bookmark ID '{bookmark_id}' not found")
            
            await self.mongodb_engine.delete(bookmark)
            return {"message": f"The bookmark has been successfully deleted for bookmark ID '{bookmark_id}'"}
        except Exception as e:
            logger.error(f"Error deleting bookmark. Bookmar ID: '{bookmark_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete bookmark for bookmark ID '{bookmark_id}': {str(e)}")

    async def login(self, user_name:str, user_password:str):
        try:
            user = await self.mongodb_engine.find_one(
                User,
                User.id == user_name
            )
            if not user: 
                logger.error(f"{user_name} login failed!")
                raise HTTPException(status_code=500, detail=f"{user_name} login failed!")
            elif user.password == user_password:
                logger.error(f"{user_name} successfully login!")
                #세션 구현
                
        except Exception as e:
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed {str(e)}")

        
    async def create_account(self, user_request: dict):
        user = await self.mongodb_engine.find_one(
                User,
                User.user_name == user_request["user_name"]
        )
        if user:
            logger.error(f"{user_request["user_name"]} already exist!")
            raise HTTPException(status_code=500, detail=f"{user_request["user_name"]} already exist!")
        try:
            user = User(
                id="1",
                email=user_request["email"] or "",
                user_name=user_request["user_name"],
                password=user_request["user_password"],
                aws_access_key_id=user_request["aws_access_key_id"] or "",
                aws_secret_access_key=user_request["aws_secret_access_key"] or "",
                openai_api_key=user_request["openai_api_key"] or "",
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None),
                updated_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            await self.mongodb_engine.save(user)
            return {"message": f"The user has been successfully created '{user_request["user_name"]}'"}
        except Exception as e:
            logger.error(f"Error adding create_account. user_name: '{user_request["user_name"]}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add create_account for user_name '{user_request["user_name"]}': {str(e)}")