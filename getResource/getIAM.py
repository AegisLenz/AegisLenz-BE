import boto3
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# AWS 세션 설정
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# IAM 클라이언트 생성
iam_client = session.client('iam')

def get_iam_users():
    iam_users = []
    users = iam_client.list_users()["Users"]

    for user in users:
        user_data = {
            "UserName": user["UserName"],
            "UserId": user["UserId"],
            "CreateDate": user["CreateDate"],
            "UserPolicies": iam_client.list_user_policies(UserName=user["UserName"])["PolicyNames"],
            "AttachedPolicies": [policy['PolicyName'] for policy in iam_client.list_attached_user_policies(UserName=user["UserName"])["AttachedPolicies"]],
            "Groups": [group['GroupName'] for group in iam_client.list_groups_for_user(UserName=user["UserName"])["Groups"]],
            "AccessKeysLastUsed": [],
            "LastUpdated": user["CreateDate"]
        }

        access_keys = iam_client.list_access_keys(UserName=user["UserName"])["AccessKeyMetadata"]
        for key in access_keys:
            key_info = iam_client.get_access_key_last_used(AccessKeyId=key["AccessKeyId"])
            user_data["AccessKeysLastUsed"].append({
                "AccessKeyId": key["AccessKeyId"],
                "Status": key["Status"],
                "LastUsedDate": key_info["AccessKeyLastUsed"].get("LastUsedDate")
            })

        iam_users.append(user_data)
    return iam_users