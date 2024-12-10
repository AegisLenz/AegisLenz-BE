import os
import asyncio
from aioboto3 import Session
from dotenv import load_dotenv


# .env 파일 로드
load_dotenv()

# AWS 세션 설정
session = Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)


async def get_iam_users():
    session = Session()
    async with session.client('iam') as iam_client:
        users = (await iam_client.list_users())["Users"]

        async def process_user(user):
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
            user_policies = (await iam_client.list_user_policies(UserName=user_name)).get("PolicyNames", [])
            for policy_name in user_policies:
                policy_details = await iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
                user_info["UserPolicies"].append({
                    "PolicyName": policy_name,
                    "PolicyDocument": policy_details["PolicyDocument"]
                })

            # 사용자에 연결된 관리형 정책 가져오기
            attached_policies = (await iam_client.list_attached_user_policies(UserName=user_name)).get("AttachedPolicies", [])
            for policy in attached_policies:
                policy_arn = policy["PolicyArn"]
                policy_details = await iam_client.get_policy(PolicyArn=policy_arn)
                default_version_id = policy_details["Policy"]["DefaultVersionId"]
                policy_version = await iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=default_version_id)
                user_info["AttachedPolicies"].append({
                    "PolicyName": policy["PolicyName"],
                    "PolicyDocument": policy_version["PolicyVersion"]["Document"]
                })

            # 사용자 그룹 가져오기
            groups = (await iam_client.list_groups_for_user(UserName=user_name)).get("Groups", [])
            user_info["Groups"] = [group["GroupName"] for group in groups]

            # 사용자 액세스 키 사용 이력 가져오기
            access_keys = (await iam_client.list_access_keys(UserName=user_name)).get("AccessKeyMetadata", [])
            for access_key in access_keys:
                access_key_id = access_key["AccessKeyId"]
                key_last_used = (await iam_client.get_access_key_last_used(AccessKeyId=access_key_id)).get("AccessKeyLastUsed", {})
                user_info["AccessKeysLastUsed"].append({
                    "AccessKeyId": access_key_id,
                    "Status": access_key["Status"],
                    "LastUsedDate": key_last_used.get("LastUsedDate", None)
                })

            return user_info

        iam_users = await asyncio.gather(*(process_user(user) for user in users))
        return iam_users


async def get_roles():
    session = Session()
    async with session.client('iam') as iam_client:
        roles = (await iam_client.list_roles())['Roles']

        async def process_role(role):
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

            # 역할에 연결된 관리형 정책 가져오기
            attached_policies = (await iam_client.list_attached_role_policies(RoleName=role_name)).get("AttachedPolicies", [])
            for policy in attached_policies:
                policy_arn = policy["PolicyArn"]
                policy_details = await iam_client.get_policy(PolicyArn=policy_arn)
                default_version_id = policy_details["Policy"]["DefaultVersionId"]
                policy_version = await iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=default_version_id)
                role_info["AttachedPolicies"].append({
                    "PolicyName": policy["PolicyName"],
                    "PolicyArn": policy_arn,
                    "PolicyDocument": policy_version["PolicyVersion"]["Document"]
                })

            # 역할 인라인 정책 가져오기
            inline_policies = (await iam_client.list_role_policies(RoleName=role_name)).get("PolicyNames", [])
            for policy_name in inline_policies:
                policy_details = await iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                role_info["InlinePolicies"].append({
                    "PolicyName": policy_name,
                    "PolicyDocument": policy_details["PolicyDocument"]
                })

            return role_info

        iam_roles = await asyncio.gather(*(process_role(role) for role in roles))
        return iam_roles
