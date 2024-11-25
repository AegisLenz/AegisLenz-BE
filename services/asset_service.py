from fastapi import Depends, HTTPException
from services.asset.get_iam import get_iam_users
from services.asset.get_s3 import get_s3_buckets
from services.asset.get_ec2 import get_ec2_instances
from models.asset_model import UserAsset, Asset, IAMUser, EC2, S3_Bucket
from repositories.asset_repository import AssetRepository
from common.logging import setup_logger

logger = setup_logger()


class AssetService:
    def __init__(self, asset_repository: AssetRepository = Depends()):
        self.asset_repository = asset_repository

    async def update_asset(self, user_id):
        try:
            # AWS에서 IAM, EC2, S3 데이터 가져오기
            iam_users = [IAMUser(**user) for user in get_iam_users()]
            ec2_instances = [EC2(**instance) for instance in get_ec2_instances()]
            s3_buckets = [S3_Bucket(**bucket) for bucket in get_s3_buckets()]
        except Exception as e:
            logger.error(f"Error collecting assets: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to collect AWS assets: {str(e)}")

        # Asset 객체 생성
        asset = Asset(IAM=iam_users, EC2=ec2_instances, S3=s3_buckets)

        # UserAsset 객체 생성 및 저장
        user_assets = UserAsset(
            user_id=user_id,
            asset=asset
        )

        try:
            await self.asset_repository.save_asset(user_assets)
            logger.debug("UserAsset saved successfully.")
        except Exception as e:
            logger.error(f"Error saving UserAsset: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save UserAsset to the database: {str(e)}")
