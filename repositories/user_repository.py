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
                raise HTTPException(status_code=404, detail="User asset not found")

            if asset_type == "EC2":
                return {"EC2": [ec2.dict() for ec2 in user_asset.asset.EC2]}
            elif asset_type == "S3_Bucket":
                return {"S3_Bucket": [bucket.dict() for bucket in user_asset.asset.S3]}
            elif asset_type == "IAMUser":
                return {"IAMUser": [iam.dict() for iam in user_asset.asset.IAM]}
            else:
                raise HTTPException(status_code=400, detail="Invalid asset type specified")
        except Exception as e:
            logger.error(f"Error fetching user asset for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching user assets")
    
    async def get_user_policies(self, user_id: str):
        try:
            user_asset = await self.mongodb_engine.find_one(
                UserAsset,
                UserAsset.user_id == user_id
            )
            # 각 IAM 유저의 AttachedPolicies를 추출하여 반환
            attached_policies_by_user = {
                iam.UserName: iam.AttachedPolicies for iam in user_asset.asset.IAM
            }
            return attached_policies_by_user
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

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
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")
