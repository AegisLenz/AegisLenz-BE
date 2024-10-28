import boto3
from dotenv import load_dotenv
import os
import json
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

def get_all_s3_bucket_details():
    """모든 S3 버킷과 해당 버킷의 상세 정보를 가져옵니다."""
    # 모든 버킷 목록 가져오기
    buckets = s3_client.list_buckets()["Buckets"]
    all_bucket_details = []

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

        # 버킷 위치 가져오기
        try:
            location = s3_client.get_bucket_location(Bucket=bucket_name)
            bucket_info["Location"] = location.get("LocationConstraint")
        except ClientError as e:
            print(f"Error fetching location for {bucket_name}: {e}")

        # 버킷 ACL 가져오기
        try:
            acl = s3_client.get_bucket_acl(Bucket=bucket_name)
            bucket_info["ACL"] = acl.get("Grants")
        except ClientError as e:
            print(f"Error fetching ACL for {bucket_name}: {e}")

        # 버킷 정책 가져오기
        try:
            policy = s3_client.get_bucket_policy(Bucket=bucket_name)
            bucket_info["Policy"] = json.loads(policy["Policy"])
        except s3_client.exceptions.NoSuchBucketPolicy:
            bucket_info["Policy"] = "No bucket policy"
        except ClientError as e:
            print(f"Error fetching policy for {bucket_name}: {e}")

        # 버킷 로깅 정보 가져오기
        try:
            logging = s3_client.get_bucket_logging(Bucket=bucket_name)
            bucket_info["Logging"] = logging.get("LoggingEnabled", "Logging not enabled")
        except ClientError as e:
            print(f"Error fetching logging for {bucket_name}: {e}")

        # 버킷 버저닝 정보 가져오기
        try:
            versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
            bucket_info["Versioning"] = versioning.get("Status", "Not enabled")
        except ClientError as e:
            print(f"Error fetching versioning for {bucket_name}: {e}")

        # 버킷 태그 가져오기
        try:
            tags = s3_client.get_bucket_tagging(Bucket=bucket_name)
            bucket_info["Tags"] = tags.get("TagSet", "No tags")
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchTagSet':
                bucket_info["Tags"] = "No tags"
            else:
                print(f"Error fetching tags for {bucket_name}: {e}")

        # 버킷 정보 출력
        all_bucket_details.append(bucket_info)
        print(json.dumps(bucket_info, default=str, indent=4))

if __name__ == "__main__":
    get_all_s3_bucket_details()