import os
import boto3
from fastapi import Depends
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta, timezone
from services.policy_service import PolicyService
from repositories.asset_repository import AssetRepository
from schemas.dashboard_schema import AccountByServiceResponseSchema, AccountCountResponseSchema, DetectionResponseSchema, ScoreResponseSchema, RisksResponseSchema
from common.logging import setup_logger

logger = setup_logger()


class DashboardService:
    def __init__(self, policy_service: PolicyService = Depends(), asset_repository: AssetRepository = Depends()):
        self.policy_service = policy_service
        self.asset_repository = asset_repository
        self.es_index = os.getenv("ES_INDEX", "cloudtrail-logs-*")
        self.es_attack_index = os.getenv("ES_ATTACK_INDEX", "cloudtrail-logs")
        self.es = Elasticsearch(
            f"{os.getenv("ES_HOST")}:{os.getenv("ES_PORT")}",
            max_retries=10, 
            retry_on_timeout=True,
            request_timeout=120
        )
        load_dotenv()
        self.session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        self.iam_client = self.session.client('iam')
        self.ec2_client = self.session.client('ec2')

    async def get_account_by_service(self, user_id: str) -> AccountByServiceResponseSchema:
        user_assets = await self.asset_repository.find_asset_by_user_id(user_id)

        # IAM, EC2, S3 개수 계산
        iam_count = len(user_assets.asset.IAM)
        ec2_count = len(user_assets.asset.EC2)
        s3_count = len(user_assets.asset.S3)
        policy_count = 0

        unique_user_policies = set()
        unique_attached_policies = set()
        
        # Policy 개수 계산
        for iam in user_assets.asset.IAM:
            for policy in iam.UserPolicies:
                unique_user_policies.add(policy.PolicyName)

            for policy in iam.AttachedPolicies:
                unique_attached_policies.add(policy.PolicyName)

        policy_count += len(unique_user_policies)
        policy_count += len(unique_attached_policies)

        total_service_count = iam_count + ec2_count + s3_count + policy_count

        return AccountByServiceResponseSchema(
            total_service_count=total_service_count,
            iam=iam_count,
            ec2=ec2_count,
            s3=s3_count,
            policy=policy_count
        )

    async def get_account_count(self, user_id: str) -> AccountCountResponseSchema:
        user_assets = await self.asset_repository.find_asset_by_user_id(user_id)

        users = len(user_assets.asset.IAM)
        roles = len(user_assets.asset.Role)
        policies = 0
        groups = 0

        unique_user_policies = set()
        unique_attached_policies = set()
        
        # Policy, Group 개수 계산
        for iam in user_assets.asset.IAM:
            for policy in iam.UserPolicies:
                unique_user_policies.add(policy.PolicyName)

            for policy in iam.AttachedPolicies:
                unique_attached_policies.add(policy.PolicyName)
                
            groups += len(iam.Groups)
        
        policies += len(unique_user_policies)
        policies += len(unique_attached_policies)

        return AccountCountResponseSchema(
            users=users,
            policies=policies,
            roles=roles,
            groups=groups
        )

    def _fetch_monthly_logs(self, index: str):
        response = self.es.search(index=index, body={
                "size": 0,
                "query": {"match_all": {}},
                "aggs": {
                    "logs_per_month": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "calendar_interval": "month",
                            "format": "yyyy-MM",
                            "time_zone": "Asia/Seoul"
                        }
                    }
                }
            }
        )
        return response["aggregations"]["logs_per_month"]["buckets"]

    def get_detection(self, user_id: str) -> DetectionResponseSchema:
        # 정상 및 공격 로그 조회
        monthly_normal_logs = self._fetch_monthly_logs(self.es_index)
        monthly_attack_logs = self._fetch_monthly_logs(self.es_attack_index)

        # 기본 월별 요약 초기화
        predefined_months = ['2024-07', '2024-08', '2024-09', '2024-10']
        monthly_detection = [
            {'month': month, 'traffic': 0, 'attack': 0} for month in predefined_months
        ]

        for normal_log in monthly_normal_logs:
            month = normal_log.get('key_as_string')
            traffic = normal_log.get('doc_count', 0)
            attack = next(
                (attack_log['doc_count'] for attack_log in monthly_attack_logs if attack_log['key_as_string'] == month),
                0
            )

            monthly_detection.append({
                'month': month,
                'traffic': traffic,
                'attack': attack
            })

        return DetectionResponseSchema(monthly_detection=monthly_detection)

    async def get_score(self, user_id: str) -> ScoreResponseSchema:
        total_log_response = self.es.count(index=self.es_index, body={"query": {"match_all": {}}})
        total_log_cnt = total_log_response['count']

        total_attack_log_response = self.es.count(index=self.es_attack_index, body={"query": {"match_all": {}}})
        total_attack_log_cnt = total_attack_log_response['count']

        user_assets = await self.asset_repository.find_asset_by_user_id(user_id)
        iam_cnt = len(user_assets.asset.IAM)

        least_privilege_policy = await self.policy_service.generate_least_privilege_policy(user_id)
        problem_iam_cnt = len(least_privilege_policy["least_privilege_policy"])

        # 단일 점수 계산
        attack_log_score = (1 - total_attack_log_cnt / total_log_cnt) * 100
        problem_iam_score = (1 - problem_iam_cnt / iam_cnt) * 100

        # 평균 점수
        score = (attack_log_score + problem_iam_score) / 2
        
        return ScoreResponseSchema(score=score)

    def _get_inactive_users_count(self, threshold_days=90) -> int:
        """90일 동안 비활성화된 사용자 수 반환"""
        now = datetime.now(timezone.utc)
        threshold_date = now - timedelta(days=threshold_days)

        inactive_count = 0
        users = self.iam_client.list_users()

        for user in users.get('Users', []):
            username = user['UserName']
            is_inactive = True

            # Check PasswordLastUsed
            user_details = self.iam_client.get_user(UserName=username)
            password_last_used = user_details.get('User', {}).get('PasswordLastUsed')
            if password_last_used and password_last_used > threshold_date:
                is_inactive = False

            # Check accessKeyLastUsed
            access_keys = self.iam_client.list_access_keys(UserName=username)
            for key in access_keys.get('AccessKeyMetadata', []):
                access_key_last_used = self.iam_client.get_access_key_last_used(AccessKeyId=key['AccessKeyId']).get('AccessKeyLastUsed', {}).get('LastUsedDate')
                if access_key_last_used and access_key_last_used > threshold_date:
                    is_inactive = False

            if is_inactive:
                inactive_count += 1

        logger.debug(f"Inactive users count: {inactive_count}")
        return inactive_count

    def _get_users_without_mfa_count(self) -> int:
        """MFA가 설정되지 않은 사용자 수 반환"""
        users_without_mfa_count = 0
        users = self.iam_client.list_users()

        for user in users.get('Users', []):
            username = user['UserName']

            # MFA 장치 조회
            mfa_devices = self.iam_client.list_mfa_devices(UserName=username)
            if not mfa_devices.get('MFADevices'):  # MFA 장치가 없는 경우
                users_without_mfa_count += 1

        logger.debug(f"Users without MFA count: {users_without_mfa_count}")
        return users_without_mfa_count

    def _check_root_mfa_enabled_count(self) -> int:
        """루트 계정의 MFA 설정 여부 반환 (0: 미설정, 1: 설정됨)"""
        summary = self.iam_client.get_account_summary()
        mfa_enabled = summary['SummaryMap'].get('AccountMFAEnabled', 0)
        logger.debug(f"Root MFA enabled: {bool(mfa_enabled)}")
        return 0 if mfa_enabled == 0 else 1

    def _count_risky_security_groups(self) -> int:
        """기본 보안 그룹에서 위험한 규칙 수 반환"""
        risky_count = 0
        response = self.ec2_client.describe_security_groups()
        security_groups = response['SecurityGroups']

        for sg in security_groups:
            for ingress_rule in sg.get('IpPermissions', []):
                for ip_range in ingress_rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == '0.0.0.0/0':
                        risky_count += 1
            for egress_rule in sg.get('IpPermissionsEgress', []):
                for ip_range in egress_rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == '0.0.0.0/0':
                        risky_count += 1

        logger.debug(f"Risky security group rules count: {risky_count}")
        return risky_count

    async def get_risks(self, user_id: str) -> RisksResponseSchema:
        # Inactive Identities
        inactive_users_count = self._get_inactive_users_count()

        # Identities with Excessive Policies
        least_privilege_policy = await self.policy_service.generate_least_privilege_policy(user_id)
        identity_with_excessive_policies = len(least_privilege_policy["least_privilege_policy"])

        # MFA Not Enabled for Users
        users_without_mfa_count = self._get_users_without_mfa_count()

        # MFA Not Enabled for Root User
        root_mfa_count = self._check_root_mfa_enabled_count()

        # Default Security Groups Allow Traffic
        risky_security_groups_count = self._count_risky_security_groups()

        return RisksResponseSchema(
            inactive_identities=inactive_users_count,
            identity_with_excessive_policies=identity_with_excessive_policies,
            MFA_not_enabled_for_users=users_without_mfa_count,
            MFA_not_enabled_for_root_user=root_mfa_count,
            default_security_groups_allow_traffic=risky_security_groups_count
        )
