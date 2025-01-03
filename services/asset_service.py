import asyncio
from fastapi import Depends, HTTPException
from services.asset.get_iam import get_iam_users, get_roles
from services.asset.get_s3 import get_s3_buckets
from services.asset.get_ec2 import get_ec2_instances
from models.asset_model import UserAsset, Asset, IAMUser, Role, EC2, S3_Bucket
from repositories.asset_repository import AssetRepository
from common.logging import setup_logger

logger = setup_logger()


class AssetService:
    def __init__(self, asset_repository: AssetRepository = Depends()):
        self.asset_repository = asset_repository

    async def update_asset(self, user_id):
        try:
            # AWS에서 IAM, Role, EC2, S3 데이터 가져오기
            iam_users, roles, ec2_instances, s3_buckets = await asyncio.gather(
                get_iam_users(),
                get_roles(),
                get_ec2_instances(),
                get_s3_buckets()
            )
            asset = Asset(IAM=iam_users, Role=roles, EC2=ec2_instances, S3=s3_buckets)
        except Exception as e:
            logger.error(f"Error collecting assets: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to collect AWS assets: {str(e)}")

        try:
            existing_user_asset = await self.asset_repository.find_asset_by_user_id(user_id)
            if existing_user_asset:
                await self.asset_repository.update_asset(user_id, asset)
                logger.debug("UserAsset updated successfully.")
            else:
                user_assets = UserAsset(
                    user_id=user_id,
                    asset=asset
                )
                await self.asset_repository.save_asset(user_assets)
                logger.debug("UserAsset created successfully.")
        except Exception as e:
            logger.error(f"Error updating UserAsset: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update UserAsset to the database: {str(e)}")