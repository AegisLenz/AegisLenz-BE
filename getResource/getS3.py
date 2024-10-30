import boto3
from dotenv import load_dotenv
import os
from botocore.exceptions import ClientError

# .env 파일 로드
load_dotenv()

# AWS 세션 설정
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# S3 클라이언트 생성
s3_client = session.client('s3')

def get_s3_buckets():
    s3_buckets = []
    buckets = s3_client.list_buckets()["Buckets"]

    for bucket in buckets:
        bucket_name = bucket["Name"]
        bucket_info = {
            "Name": bucket_name,
            "CreationDate": bucket["CreationDate"],
            "Location": None,
            "ACL": None,
            "Policy": None,
            "Logging": None,
            "Versioning": None,
            "Tags": None
        }

        try:
            bucket_info["Location"] = s3_client.get_bucket_location(Bucket=bucket_name).get("LocationConstraint")
            bucket_info["ACL"] = s3_client.get_bucket_acl(Bucket=bucket_name).get("Grants")
            
            # 버킷 정책 가져오기
            try:
                policy = s3_client.get_bucket_policy(Bucket=bucket_name).get("Policy")
                bucket_info["Policy"] = policy
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                    bucket_info["Policy"] = "No bucket policy"
                else:
                    print(f"Error fetching policy for {bucket_name}: {e}")
            
            bucket_info["Logging"] = s3_client.get_bucket_logging(Bucket=bucket_name).get("LoggingEnabled")
            bucket_info["Versioning"] = s3_client.get_bucket_versioning(Bucket=bucket_name).get("Status")

            # 버킷 태그 가져오기
            try:
                tags = s3_client.get_bucket_tagging(Bucket=bucket_name).get("TagSet")
                bucket_info["Tags"] = tags
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchTagSet':
                    bucket_info["Tags"] = "No tags"
                else:
                    print(f"Error fetching tags for {bucket_name}: {e}")

        except Exception as e:
            print(f"Error fetching data for {bucket_name}: {e}")

        s3_buckets.append(bucket_info)
    return s3_buckets