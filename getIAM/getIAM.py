import boto3
from dotenv import load_dotenv
import os
import json

# .env 파일 로드
load_dotenv()

# AWS 세션 설정
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# EC2 클라이언트 생성
ec2_client = session.client('ec2')

def get_ec2_instances():
    """모든 EC2 인스턴스 정보를 JSON 형식으로 가져옵니다."""
    instances = ec2_client.describe_instances()["Reservations"]
    print("EC2 Instances:")
    for reservation in instances:
        for instance in reservation["Instances"]:
            print(json.dumps(instance, default=str, indent=4))

if __name__ == "__main__":
    get_ec2_instances()