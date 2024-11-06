import asyncio
from core.mongodb_driver import mongodb
from models.asset_model import UserAsset, Asset, IAMUser, EC2, S3_Bucket
from utils.asset.get_iam import get_iam_users
from utils.asset.get_s3 import get_s3_buckets
from utils.asset.get_ec2 import get_ec2_instances

async def insert_data(user_id):
    # IAM, EC2, S3 데이터 수집
    iam_users = [IAMUser(**user) for user in get_iam_users()]
    ec2_instances = [EC2(**instance) for instance in get_ec2_instances()]
    s3_buckets = [S3_Bucket(**bucket) for bucket in get_s3_buckets()]

    # Asset 객체 생성
    asset = Asset(IAM=iam_users, EC2=ec2_instances, S3=s3_buckets)
    
    # UserAsset 객체 생성 및 저장
    user_asset = UserAsset(
        user_id=user_id,
        asset=asset  # 중첩된 Asset 객체를 포함하여 저장
    )
    print(user_asset)
    engine = mongodb.get_engine()
    await engine.save(user_asset)  # UserAsset 저장 시 Asset 필드도 중첩 저장
    print("Data inserted/updated in MongoDB")

# 실행 코드
if __name__ == "__main__":
    user_id = input("Insert User ID: ")

    async def main():
        await mongodb.connect()
        await insert_data(user_id)
        await mongodb.close()

    asyncio.run(main())