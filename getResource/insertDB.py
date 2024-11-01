import asyncio
from core.mongodb_driver import mongodb
from models.asset_model import UserResource, Resource, IAMUser, EC2, S3_Bucket
from getResource.getIAM import get_iam_users
from getResource.getS3 import get_s3_buckets
from getResource.getEC2 import get_ec2_instances

async def insert_data(user_id):
    # IAM, EC2, S3 데이터 수집
    iam_users = [IAMUser(**user) for user in get_iam_users()]
    ec2_instances = [EC2(**instance) for instance in get_ec2_instances()]
    s3_buckets = [S3_Bucket(**bucket) for bucket in get_s3_buckets()]

    # Resource 객체 생성
    resource = Resource(IAM=iam_users, EC2=ec2_instances, S3=s3_buckets)
    
    # UserResource 객체 생성 및 저장
    user_resource = UserResource(
        id=user_id,
        resource=resource  # 중첩된 Resource 객체를 포함하여 저장
    )
    print(user_resource)
    async for engine in mongodb.get_engine():
        await engine.save(user_resource)  # UserResource 저장 시 resource 필드도 중첩 저장
        print("Data inserted/updated in MongoDB")

# 실행 코드
if __name__ == "__main__":
    user_id = input("Insert User ID: ")

    async def main():
        await mongodb.connect()
        await insert_data(user_id)
        await mongodb.close()

    asyncio.run(main())