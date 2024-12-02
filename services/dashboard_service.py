from fastapi import Depends
from repositories.asset_repository import AssetRepository
from schemas.dashboard_schema import AccountByServiceResponseSchema


class DashboardService:
    def __init__(self, asset_repository: AssetRepository = Depends()):
        self.asset_repository = asset_repository

    async def get_account_by_service(self, user_id: str) -> AccountByServiceResponseSchema:
        user_assets = await self.asset_repository.find_asset_by_user_id(user_id)

        # IAM, EC2, S3 개수 계산
        iam_count = len(user_assets.asset.IAM)
        ec2_count = len(user_assets.asset.EC2)
        s3_count = len(user_assets.asset.S3)

        policy_count = 0

        unique_user_policies = set()
        unique_attached_policies = set()
        
        # Policy 개수 계산
        for iam in user_assets.asset.IAM:
            for policy in iam.UserPolicies:
                unique_user_policies.add(policy["PolicyName"])

            for policy in iam.AttachedPolicies:
                unique_attached_policies.add(policy["PolicyName"])

        policy_count += len(unique_user_policies)
        policy_count += len(unique_attached_policies)

        return AccountByServiceResponseSchema(
            iam=iam_count,
            ec2=ec2_count,
            s3=s3_count,
            policy=policy_count
        )
