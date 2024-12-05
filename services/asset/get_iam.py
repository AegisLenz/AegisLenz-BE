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

# IAM 및 CloudTrail 클라이언트 생성
iam_client = session.client('iam')

# IAM 사용자 정보를 가져오는 함수
def get_iam_users():
    iam_users = []
    users = iam_client.list_users()["Users"]

    for user in users:
        user_name = user["UserName"]
        user_info = {
            "UserName": user_name,
            "UserId": user.get("UserId", ""),
            "CreateDate": user.get("CreateDate"),
            "UserPolicies": [],
            "AttachedPolicies": [],
            "Groups": [],
            "PasswordLastUsed": user.get("PasswordLastUsed"),
            "AccessKeysLastUsed": [],
            "LastUpdated": user.get("LastUpdated")
        }

        # 사용자 정책 가져오기
        user_policies = iam_client.list_user_policies(UserName=user_name).get("PolicyNames", [])
        for policy_name in user_policies:
            
            # 정책의 내용 가져오기
            policy_details = iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
            policy_document = policy_details["PolicyDocument"]
            
            user_info["UserPolicies"].append({
                "PolicyName": policy_name,
                "PolicyDocument": policy_document
            })

        # 사용자에 연결된 관리형 정책 가져오기
        attached_policies = iam_client.list_attached_user_policies(UserName=user_name).get("AttachedPolicies", [])
        for policy in attached_policies:
            policy_arn = policy.get("PolicyArn", None)

            # 1. 최신 버전 ID를 가져오기 위해 get_policy 호출
            policy_details = iam_client.get_policy(PolicyArn=policy_arn)
            default_version_id = policy_details["Policy"]["DefaultVersionId"]

            # 2. 정책의 최신 버전 내용 가져오기
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=default_version_id
            )

            policy_document = policy_version["PolicyVersion"]["Document"]
            user_info["AttachedPolicies"].append({
                "PolicyName": policy["PolicyName"],
                "PolicyDocument": policy_document
            })

        # 사용자 그룹 가져오기
        groups = iam_client.list_groups_for_user(UserName=user_name).get("Groups", [])
        user_info["Groups"] = [group["GroupName"] for group in groups]

        # 사용자 액세스 키 사용 이력 가져오기
        access_keys = iam_client.list_access_keys(UserName=user_name).get("AccessKeyMetadata", [])
        for access_key in access_keys:
            access_key_id = access_key["AccessKeyId"]
            key_last_used = iam_client.get_access_key_last_used(AccessKeyId=access_key_id).get("AccessKeyLastUsed", {})
            user_info["AccessKeysLastUsed"].append({
                "AccessKeyId": access_key_id,
                "Status": access_key["Status"],
                "LastUsedDate": key_last_used.get("LastUsedDate", None)
            })

        iam_users.append(user_info)
    
    return iam_users


# IAM 역할 정보를 가져오는 함수
def get_roles():
    iam_roles = []
    roles = iam_client.list_roles()['Roles']
    for role in roles:
        role_name = role["RoleName"]
        role_info = {
            "Path": role.get("Path"),
            "RoleName": role_name,
            "RoleId": role.get("RoleId"),
            "Arn": role.get("Arn"),
            "CreateDate": role.get("CreateDate"),
            "AssumeRolePolicyDocument": role.get("AssumeRolePolicyDocument", {}),
            "Description": role.get("Description", ""),
            "MaxSessionDuration": role.get("MaxSessionDuration"),
            "PermissionsBoundary": role.get("PermissionsBoundary", {}),
            "Tags": role.get("Tags", []),
            "AttachedPolicies": [],
            "InlinePolicies": []
        }

        # 관리형 정책 가져오기
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name).get("AttachedPolicies", [])
        for policy in attached_policies:
            policy_arn = policy.get("PolicyArn", None)

            # 관리형 정책의 기본 버전 가져오기
            policy_details = iam_client.get_policy(PolicyArn=policy_arn)
            default_version_id = policy_details["Policy"]["DefaultVersionId"]

            # 관리형 정책의 내용 가져오기
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=default_version_id
            )
            policy_document = policy_version["PolicyVersion"]["Document"]

            role_info["AttachedPolicies"].append({
                "PolicyName": policy["PolicyName"],
                "PolicyArn": policy_arn,
                "PolicyDocument": policy_document
            })

        # 인라인 정책 가져오기
        inline_policies = iam_client.list_role_policies(RoleName=role_name).get("PolicyNames", [])
        for policy_name in inline_policies:
            # 인라인 정책 내용 가져오기
            policy_details = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            role_info["InlinePolicies"].append({
                "PolicyName": policy_name,
                "PolicyDocument": policy_details["PolicyDocument"]
            })

        iam_roles.append(role_info)

    return iam_roles
