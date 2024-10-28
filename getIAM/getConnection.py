import boto3
from dotenv import load_dotenv
from datetime import datetime
import os
import json

# .env 파일 로드
load_dotenv()

# AWS 설정
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
iam_client = session.client("iam")

def check_user_permissions(user_name):
    """특정 IAM 사용자가 EC2 또는 S3에 접근 권한이 있는지 확인"""
    
    # 사용자의 관리형 정책 목록 가져오기
    attached_policies = iam_client.list_attached_user_policies(UserName=user_name)["AttachedPolicies"]
    
    # EC2 및 S3 권한 체크를 위한 설정
    target_services = ["ec2", "s3"] 
    ec2_permissions = []
    s3_permissions = []
    
    for policy in attached_policies:
        # 정책 ARN 가져오기
        policy_arn = policy["PolicyArn"]
        
        # 정책 정보 가져오기
        policy_details = iam_client.get_policy(PolicyArn=policy_arn)["Policy"]
        
        # 정책 버전 가져오기
        policy_version = policy_details["DefaultVersionId"]
        policy_document = iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=policy_version)["PolicyVersion"]["Document"]
        
        # 정책의 각 Statement 분석
        for statement in policy_document["Statement"]:
            effect = statement.get("Effect")
            actions = statement.get("Action", [])
            if effect == "Allow":
                if isinstance(actions, str):  # 단일 액션일 경우 리스트로 변환
                    actions = [actions]
                
                # EC2와 S3에 대한 액션만 필터링
                for action in actions:
                    if action.startswith("ec2:"):
                        ec2_permissions.append(action)
                    elif action.startswith("s3:"):
                        s3_permissions.append(action)
    
    # 결과 출력
    if ec2_permissions:
        print(f"User {user_name} has the following EC2 permissions:")
        for permission in ec2_permissions:
            print(f"  - {permission}")
    else:
        print(f"User {user_name} has no EC2 permissions.")
    
    if s3_permissions:
        print(f"User {user_name} has the following S3 permissions:")
        for permission in s3_permissions:
            print(f"  - {permission}")
    else:
        print(f"User {user_name} has no S3 permissions.")

# 사용자의 EC2 및 S3 권한 확인
check_user_permissions("Wonje_Cha")