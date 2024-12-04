import os
from fastapi import Depends
from elasticsearch import Elasticsearch
from services.policy_service import PolicyService
from repositories.asset_repository import AssetRepository
from schemas.dashboard_schema import AccountByServiceResponseSchema, AccountCountResponseSchema, DetectionResponseSchema, ScoreResponseSchema
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
