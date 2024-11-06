from models.user_model import User
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from core.mongodb_driver import mongodb
from models.asset_model import UserAsset


class UserRepository:
    def __init__(self):
        self.user = User(name="John Doe", age=30, email="johndoe@example.com")  # 테스트 유저 데이터

    async def save_user(self, engine):
        new_user = await engine.save(self.user)
        return new_user
    
    async def get_user_asset(self, user_id: str, Assettype: str,engine):
        user_asset = await engine.find_one(UserAsset, {"user_id": user_id})
        if not user_asset:
            return {"error": "User asset not found"}

        # 반환 형식 { EC2 : [{}, {}, {}] }
        if Assettype == "EC2":
            return {"EC2": [ec2.dict() for ec2 in user_asset.asset.EC2]}
        elif Assettype == "S3_Bucket":
            return {"S3_Bucket": [bucket.dict() for bucket in user_asset.asset.S3]}
        elif Assettype == "IAMUser":
            return {"IAMUser": [iam.dict() for iam in user_asset.asset.IAM]}
        else:
            return {"error": "Invalid asset type specified"}