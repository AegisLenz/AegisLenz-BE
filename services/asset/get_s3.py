import os
import asyncio
from aioboto3 import Session
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import json

# .env 파일 로드
load_dotenv()

# AWS 세션 생성
session = Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

async def get_s3_buckets():
    async with session.client('s3') as s3_client:
        s3_buckets = []
        buckets = (await s3_client.list_buckets())["Buckets"]

        async def process_bucket(bucket):
            bucket_name = bucket["Name"]
            bucket_info = {
                "Name": bucket_name,
                "CreationDate": bucket["CreationDate"],
                "Location": None,
                "ACL": [],
                "Policy": {},
                "Logging": None,
                "Versioning": None,
                "Tags": []
            }

            try:
                bucket_info["Location"] = (await s3_client.get_bucket_location(Bucket=bucket_name)).get("LocationConstraint")
                bucket_info["ACL"] = (await s3_client.get_bucket_acl(Bucket=bucket_name)).get("Grants", [])
                
                # 버킷 정책 가져오기
                try:
                    policy = (await s3_client.get_bucket_policy(Bucket=bucket_name)).get("Policy")
                    bucket_info["Policy"] = json.loads(policy) if policy else {}
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                        bucket_info["Policy"] = {}
                    else:
                        print(f"Error fetching policy for {bucket_name}: {e}")
                
                bucket_info["Logging"] = (await s3_client.get_bucket_logging(Bucket=bucket_name)).get("LoggingEnabled")
                bucket_info["Versioning"] = (await s3_client.get_bucket_versioning(Bucket=bucket_name)).get("Status")

                # 버킷 태그 가져오기
                try:
                    tags = (await s3_client.get_bucket_tagging(Bucket=bucket_name)).get("TagSet", [])
                    bucket_info["Tags"] = tags
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchTagSet':
                        bucket_info["Tags"] = []
                    else:
                        print(f"Error fetching tags for {bucket_name}: {e}")

            except Exception as e:
                print(f"Error fetching data for {bucket_name}: {e}")

            return bucket_info

        # 모든 버킷 병렬 처리
        s3_buckets = await asyncio.gather(*(process_bucket(bucket) for bucket in buckets))
        return s3_buckets
