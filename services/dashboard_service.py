import os
import boto3
from fastapi import Depends, HTTPException
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from datetime import datetime, timedelta, timezone
from services.policy_service import PolicyService
from services.gpt_service import GPTService
from repositories.asset_repository import AssetRepository
from repositories.bert_repository import BertRepository
from repositories.report_repository import ReportRepository
from schemas.dashboard_schema import AccountByServiceResponseSchema, AccountCountResponseSchema, DetectionResponseSchema, ScoreResponseSchema, RisksResponseSchema, ReportCheckResponseSchema, ReportSummary
from common.logging import setup_logger

logger = setup_logger()
load_dotenv()


class DashboardService:
    def __init__(self, policy_service: PolicyService = Depends(), gpt_service: GPTService = Depends(),
                 asset_repository: AssetRepository = Depends(), bert_repository: BertRepository = Depends(),
                 report_repository: ReportRepository = Depends()):
        self.policy_service = policy_service
        self.gpt_service = gpt_service
        self.asset_repository = asset_repository
        self.bert_repository = bert_repository
        self.report_repository = report_repository

        self.es_index = os.getenv("ES_INDEX", "cloudtrail-logs-*")
        self.es_attack_index = os.getenv("ES_ATTACK_INDEX", "cloudtrail-attack-logs")
        try:
            self.es = Elasticsearch(
                f"{os.getenv('ES_HOST')}:{os.getenv('ES_PORT')}",
                max_retries=10,
                retry_on_timeout=True,
                request_timeout=120
            )
        except es_exceptions.ElasticsearchException as e:
            logger.error(f"Elasticsearch initialization error: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize Elasticsearch client.")

        try:
            self.session = boto3.Session(
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )
            self.iam_client = self.session.client('iam')
            self.ec2_client = self.session.client('ec2')
        except Exception as e:
            logger.error(f"AWS session initialization error: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize AWS session.")

        try:
            self.init_prompts = self.gpt_service._load_prompts()
            logger.debug("Successfully loaded initial prompts.")
        except Exception as e:
            logger.error(f"Initial prompts load error: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize prompts.")

    async def get_account_by_service(self, user_id: str) -> AccountByServiceResponseSchema:
        try:
            user_assets = await self.asset_repository.find_asset_by_user_id(user_id)
            if not user_assets:
                raise HTTPException(status_code=404, detail=f"No assets found for user_id: {user_id}")

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
                    unique_user_policies.add(policy["PolicyName"])

                for policy in iam.AttachedPolicies:
                    unique_attached_policies.add(policy["PolicyName"])

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
        except Exception as e:
            logger.error(f"Error in get_account_by_service for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch account by service.")

    async def get_account_count(self, user_id: str) -> AccountCountResponseSchema:
        try:
            user_assets = await self.asset_repository.find_asset_by_user_id(user_id)
            if not user_assets:
                raise HTTPException(status_code=404, detail=f"No assets found for user_id: {user_id}")

            users = len(user_assets.asset.IAM)
            roles = len(user_assets.asset.Role)
            policies = 0
            groups = 0

            unique_user_policies = set()
            unique_attached_policies = set()

            # Policy, Group 개수 계산
            for iam in user_assets.asset.IAM:
                for policy in iam.UserPolicies:
                    unique_user_policies.add(policy["PolicyName"])

                for policy in iam.AttachedPolicies:
                    unique_attached_policies.add(policy["PolicyName"])

                groups += len(iam.Groups)

            policies += len(unique_user_policies)
            policies += len(unique_attached_policies)

            return AccountCountResponseSchema(
                users=users,
                policies=policies,
                roles=roles,
                groups=groups
            )
        except Exception as e:
            logger.error(f"Error in get_account_count for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch account count.")

    def _fetch_monthly_logs(self, index: str):
        try:
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
        except es_exceptions.NotFoundError:
            raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")
        except es_exceptions.ElasticsearchException as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching total log count: {str(e)}")

    def get_detection(self, user_id: str) -> DetectionResponseSchema:
        try:
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
        except Exception as e:
            logger.error(f"Error in get_detection for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch detection data.")

    async def get_score(self, user_id: str) -> ScoreResponseSchema:
        try:
            try:
                # 전체 로그 개수 가져오기
                total_log_response = self.es.count(index=self.es_index, body={"query": {"match_all": {}}})
                total_log_cnt = total_log_response['count']
            except es_exceptions.NotFoundError:
                raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")
            except es_exceptions.ElasticsearchException as e:
                raise HTTPException(status_code=500, detail=f"An error occurred while fetching total log count: {str(e)}")

            try:
                # 공격 로그 개수 가져오기
                total_attack_log_response = self.es.count(index=self.es_attack_index, body={"query": {"match_all": {}}})
                total_attack_log_cnt = total_attack_log_response['count']
            except es_exceptions.NotFoundError:
                raise HTTPException(status_code=404, detail=f"Index '{self.es_attack_index}' not found.")
            except es_exceptions.ElasticsearchException as e:
                raise HTTPException(status_code=500, detail=f"An error occurred while fetching total attack log count: {str(e)}")

            try:
                # 사용자 자산 정보 가져오기
                user_assets = await self.asset_repository.find_asset_by_user_id(user_id)
                if not user_assets or not hasattr(user_assets.asset, 'IAM'):
                    raise HTTPException(status_code=404, detail=f"No assets found for user_id: {user_id}")
                iam_cnt = len(user_assets.asset.IAM)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error fetching assets for user_id {user_id}: {str(e)}")

            try:
                # 최소 권한 정책 생성
                least_privilege_policy = await self.policy_service.generate_least_privilege_policy(user_id)
                problem_iam_cnt = len(least_privilege_policy["least_privilege_policy"])
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error generating least privilege policy for user_id {user_id}: {str(e)}")

            # 단일 점수 계산
            attack_log_score = (1 - total_attack_log_cnt / total_log_cnt) * 100
            problem_iam_score = (1 - problem_iam_cnt / iam_cnt) * 100

            # 평균 점수
            score = (attack_log_score + problem_iam_score) / 2
            
            return ScoreResponseSchema(score=score)
        except Exception as e:
            logger.error(f"Error calculating score for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate user score.")

    def _calculate_inactive_users(self, threshold_days=90) -> int:
        """90일 동안 비활성화된 사용자 수 반환"""
        try:
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

            return inactive_count
        except Exception as e:
            logger.error(f"Error calculating inactive users: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate inactive users.")

    def _get_users_without_mfa_count(self) -> int:
        """MFA가 설정되지 않은 사용자 수 반환"""
        try:
            users_without_mfa_count = 0
            users = self.iam_client.list_users()

            for user in users.get('Users', []):
                username = user['UserName']

                # MFA 장치 조회
                mfa_devices = self.iam_client.list_mfa_devices(UserName=username)
                if not mfa_devices.get('MFADevices'):  # MFA 장치가 없는 경우
                    users_without_mfa_count += 1
            
            return users_without_mfa_count
        except Exception as e:
            logger.error(f"Error counting users without MFA: {e}")
            raise HTTPException(status_code=500, detail="Failed to count users without MFA.")

    def _check_root_mfa_enabled_count(self) -> int:
        """루트 계정의 MFA 설정 여부 반환 (0: 미설정, 1: 설정됨)"""
        try:
            summary = self.iam_client.get_account_summary()
            mfa_enabled = summary['SummaryMap'].get('AccountMFAEnabled', 0)
            return 0 if mfa_enabled == 0 else 1
        except Exception as e:
            logger.error(f"Error checking root MFA status: {e}")
            raise HTTPException(status_code=500, detail="Failed to check root MFA status.")

    def _count_risky_security_groups(self) -> int:
        """기본 보안 그룹에서 위험한 규칙 수 반환"""
        try:
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

            return risky_count
        except Exception as e:
            logger.error(f"Error counting risky security groups: {e}")
            raise HTTPException(status_code=500, detail="Failed to count risky security group rules.")

    async def get_risks(self, user_id: str) -> RisksResponseSchema:
        try:
            # Inactive users
            inactive_users_count = self._calculate_inactive_users()
            logger.debug(f"Inactive users count: {inactive_users_count}")

            # Excessive policies
            least_privilege_policy = await self.policy_service.generate_least_privilege_policy(user_id)
            identity_with_excessive_policies = len(least_privilege_policy["least_privilege_policy"])
            logger.debug(f"Identities with excessive policies: {identity_with_excessive_policies}")

            # MFA Not Enabled for Users
            users_without_mfa_count = self._get_users_without_mfa_count()
            logger.debug(f"Users without MFA: {users_without_mfa_count}")

            # MFA Not Enabled for Root User
            root_mfa_count = self._check_root_mfa_enabled_count()
            logger.debug(f"Root MFA enabled count: {root_mfa_count}")

            # Default Security Groups Allow Traffic
            risky_security_groups_count = self._count_risky_security_groups()
            logger.debug(f"Risky security groups count: {risky_security_groups_count}")

            return RisksResponseSchema(
                inactive_identities=inactive_users_count,
                identity_with_excessive_policies=identity_with_excessive_policies,
                MFA_not_enabled_for_users=users_without_mfa_count,
                MFA_not_enabled_for_root_user=root_mfa_count,
                default_security_groups_allow_traffic=risky_security_groups_count
            )
        except Exception as e:
            logger.error(f"Error fetching risks for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch user risk data.")

    async def get_report_check(self, user_id: str) -> ReportCheckResponseSchema:
        try:
            reports = await self.report_repository.find_reports_by_user_id(user_id)
            if not reports:
                raise HTTPException(status_code=404, detail=f"No reports found for user_id: {user_id}")
            
            try:
                report_check_content = self.init_prompts["ReportCheck"][0]["content"].format(
                    totalreport=reports
                )
            except KeyError as e:
                logger.error(f"Prompt key missing for ReportCheck: {e}")
                raise HTTPException(status_code=500, detail="Failed to format GPT prompt.")

            report_check_prompt = [{"role": "system", "content": report_check_content}]
            logger.debug(f"Generated GPT prompt for user_id: {user_id}")

            response = await self.gpt_service.get_response(report_check_prompt, json_format=False)
            logger.debug(f"GPT response received for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error fetching GPT response for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to process GPT response.")

        try:
            report_lines = [line.strip().strip("\"") for line in response.splitlines() if line.strip()]
            if len(report_lines) != len(reports):
                logger.error("Mismatch between GPT response and reports count.")
                raise HTTPException(status_code=500, detail="Mismatch between GPT response and reports.")

            report_check = [
                ReportSummary(report_id=report.id, summary=line)
                for report, line in zip(reports, report_lines)
            ]
            logger.info(f"Report check generated for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error processing GPT response for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Error processing report summaries.")

        return ReportCheckResponseSchema(report_check=report_check)
