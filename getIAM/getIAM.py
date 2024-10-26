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

def fetch_last_access_for_user(user_name):
    """특정 사용자의 Access Key Last Accessed 정보를 가져옵니다."""
    access_keys = iam_client.list_access_keys(UserName=user_name)["AccessKeyMetadata"]
    last_access_info = []
    
    # 각 액세스 키의 마지막 사용 날짜 가져오기
    for access_key in access_keys:
        last_access = iam_client.get_access_key_last_used(AccessKeyId=access_key["AccessKeyId"])
        last_access_time = last_access.get("AccessKeyLastUsed", {}).get("LastUsedDate")
        if last_access_time:
            last_access_time = last_access_time.isoformat()  # datetime -> ISO 포맷 문자열로 변환
        last_access_info.append({
            "AccessKeyId": access_key["AccessKeyId"],
            "Status": access_key["Status"],
            "LastUsedDate": last_access_time
        })
    
    return last_access_info

def fetch_user_data(user_name):
    """특정 사용자의 IAM 정보를 JSON 파일로 저장"""
    try:
        user = iam_client.get_user(UserName=user_name)["User"]
        
        # 사용자 정책 정보 가져오기 (인라인 정책)
        user_policies = iam_client.list_user_policies(UserName=user["UserName"])["PolicyNames"]
        
        # 관리형 정책 정보 가져오기
        attached_policies = iam_client.list_attached_user_policies(UserName=user["UserName"])["AttachedPolicies"]
        attached_policy_names = [policy["PolicyName"] for policy in attached_policies]
        
        # 사용자 그룹 정보 가져오기
        user_groups = iam_client.list_groups_for_user(UserName=user["UserName"])["Groups"]
        
        # Last Access 정보 가져오기
        last_access_info = fetch_last_access_for_user(user["UserName"])

        user_data = {
            "UserName": user["UserName"],
            "UserId": user["UserId"],
            "CreateDate": user["CreateDate"].isoformat(),  # datetime -> ISO 포맷 문자열로 변환
            "UserPolicies": user_policies,
            "AttachedPolicies": attached_policy_names,
            "Groups": [group["GroupName"] for group in user_groups],
            "AccessKeysLastUsed": last_access_info,
            "LastUpdated": datetime.now().isoformat()  # datetime -> ISO 포맷 문자열로 변환
        }
        
        # JSON 파일로 저장
        file_name = f"{user_name}_IAM_data.json"
        with open(file_name, "w") as json_file:
            json.dump(user_data, json_file, indent=4)
        
        print(f"IAM User Data for {user_name} saved to {file_name}")
    except iam_client.exceptions.NoSuchEntityException:
        print(f"No user found with UserName: {user_name}")

if __name__ == "__main__":
    fetch_user_data("Wonje_Cha")