import os
import json
import asyncio
from aioboto3 import Session
from fastapi import Depends, HTTPException
from dotenv import load_dotenv
from datetime import date, timedelta, datetime, timezone
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.policy_service import PolicyService
from services.gpt_service import GPTService
from services.dashboard.daily_insight import process_logs_by_token_limit
from services.policy.filter_original_policy import filter_original_policy
from repositories.asset_repository import AssetRepository
from repositories.bert_repository import BertRepository
from repositories.report_repository import ReportRepository
from repositories.prompt_repository import PromptRepository
from repositories.dashboard_repository import DashboardRepository
from schemas.dashboard_schema import AccountByServiceResponseSchema, AccountCountResponseSchema, DetectionResponseSchema, ScoreResponseSchema, RisksResponseSchema, ReportCheckResponseSchema, ReportSummary, DailyInsightResponseSchema
from common.logging import setup_logger

logger = setup_logger()
load_dotenv()


class DashboardService:
    def __init__(self, policy_service: PolicyService = Depends(), gpt_service: GPTService = Depends(),
                 asset_repository: AssetRepository = Depends(), bert_repository: BertRepository = Depends(),
                 report_repository: ReportRepository = Depends(), prompt_repository: PromptRepository = Depends(),
                 dashboard_repository: DashboardRepository = Depends()):
        self.policy_service = policy_service
        self.gpt_service = gpt_service
        self.asset_repository = asset_repository
        self.bert_repository = bert_repository
        self.report_repository = report_repository
        self.prompt_repository = prompt_repository
        self.dashboard_repository = dashboard_repository

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
            self.init_prompts = self.gpt_service._load_prompts()
            logger.debug("Successfully loaded initial prompts.")
        except Exception as e:
            logger.error(f"Failed to load initial prompts: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize prompts.")

        try:
            self.session = Session(
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )
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
                problem_iam = filter_original_policy(least_privilege_policy["original_policy"], least_privilege_policy["least_privilege_policy"])
                problem_iam_cnt = len(problem_iam)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error generating least privilege policy for user_id {user_id}: {str(e)}")

            # 단일 점수 계산
            if total_log_cnt == 0 or iam_cnt == 0:
                raise ValueError("Division by zero detected in total_log_cnt or iam_cnt.")
            
            attack_log_score = (1 - total_attack_log_cnt / total_log_cnt) * 100
            problem_iam_score = (1 - problem_iam_cnt / iam_cnt) * 100

            # 평균 점수
            score = (attack_log_score * 0.3) + (problem_iam_score * 0.7)
            return ScoreResponseSchema(score=score)
        except Exception as e:
            logger.error(f"Error calculating score for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate user score.")

    async def _get_inactive_users(self, threshold_days=90) -> int:
        """90일 동안 비활성화된 사용자의 UserName 반환"""
        try:
            now = datetime.now(timezone.utc)
            threshold_date = now - timedelta(days=threshold_days)

            inactive_users = []
            async with self.session.client('iam') as iam_client:
                users = await iam_client.list_users()

                for user in users.get('Users', []):
                    username = user['UserName']
                    is_inactive = True

                    # Check PasswordLastUsed
                    user_details = await iam_client.get_user(UserName=username)
                    password_last_used = user_details.get('User', {}).get('PasswordLastUsed')
                    if password_last_used and password_last_used > threshold_date:
                        is_inactive = False

                    # Check accessKeyLastUsed
                    access_keys = await iam_client.list_access_keys(UserName=username)
                    for key in access_keys.get('AccessKeyMetadata', []):
                        access_key_last_used_response = await iam_client.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
                        access_key_last_used = access_key_last_used_response.get('AccessKeyLastUsed', {}).get('LastUsedDate')
                        if access_key_last_used and access_key_last_used > threshold_date:
                            is_inactive = False

                    if is_inactive:
                        inactive_users.append(username)

                return inactive_users
        except Exception as e:
            logger.error(f"Error retrieving inactive users: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve inactive users.")

    async def _get_users_without_mfa(self) -> int:
        """MFA가 설정되지 않은 사용자의 UserName 반환"""
        try:
            users_without_mfa = []
            async with self.session.client('iam') as iam_client:
                users = await iam_client.list_users()

                for user in users.get('Users', []):
                    username = user['UserName']

                    # MFA 장치 조회
                    mfa_devices = await iam_client.list_mfa_devices(UserName=username)
                    if not mfa_devices.get('MFADevices'):  # MFA 장치가 없는 경우
                        users_without_mfa.append(username)
                
                return users_without_mfa
        except Exception as e:
            logger.error(f"Error retrieving users without MFA: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve users without MFA.")

    async def _check_root_mfa_enabled(self) -> int:
        """루트 계정의 MFA 설정 여부 반환 (0: 미설정, 1: 설정됨)"""
        try:
            async with self.session.client('iam') as iam_client:
                summary = await iam_client.get_account_summary()
                mfa_enabled = summary['SummaryMap'].get('AccountMFAEnabled', 0)
                return 0 if mfa_enabled == 0 else 1
        except Exception as e:
            logger.error(f"Error checking root MFA status: {e}")
            raise HTTPException(status_code=500, detail="Failed to check root MFA status.")

    async def _count_risky_security_groups(self) -> int:
        """기본 보안 그룹에서 위험한 규칙 수 반환"""
        try:
            risky_count = 0
            async with self.session.client('ec2') as ec2_client:
                response = await ec2_client.describe_security_groups()
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

    def _extract_excessive_policies(self, least_privilege_policy: dict) -> set[str]:
        """과도한 정책이 적용된 사용자 식별"""
        identity_with_excessive_policies = set()
        least_privilege_data = least_privilege_policy.get("least_privilege_policy", {})
        
        if not isinstance(least_privilege_data, dict):
            logger.warning("Invalid data format for least_privilege_policy.")
            return identity_with_excessive_policies

        for user, policies in least_privilege_data.items():
            if not isinstance(policies, list):
                logger.warning(f"Invalid policy format for user {user}. Skipping.")
                continue

            for policy in policies:
                policy_name = policy.get('PolicyName')
                if policy_name:
                    identity_with_excessive_policies.add(policy_name)
                else:
                    logger.warning(f"Policy for user {user} is missing 'PolicyName'. Skipping.")
        
        return identity_with_excessive_policies

    async def get_risks(self, user_id: str) -> RisksResponseSchema:
        try:
            inactive_users, least_privilege_policy, users_without_mfa, is_root_mfa, risky_security_groups_count = await asyncio.gather(
                self._get_inactive_users(),
                self.policy_service.generate_least_privilege_policy(user_id),
                self._get_users_without_mfa(),
                self._check_root_mfa_enabled(),
                self._count_risky_security_groups()
            )

            return RisksResponseSchema(
                inactive_identities=inactive_users,
                identity_with_excessive_policies=self._extract_excessive_policies(least_privilege_policy),
                MFA_not_enabled_for_users=users_without_mfa,
                MFA_not_enabled_for_root_user=is_root_mfa,
                default_security_groups_allow_traffic=risky_security_groups_count
            )
        except Exception as e:
            logger.error(f"Error fetching risks for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch user risk data.")

    async def get_report_check(self, user_id: str) -> ReportCheckResponseSchema:
        try:
            reports = await self.report_repository.find_reports_by_user_id(user_id)
            if not reports:
                return ReportCheckResponseSchema(report_check=[])
            
            report_check = []
            for report in reports:
                try:
                    report_check_content = self.init_prompts["ReportCheck"][0]["content"].format(
                        report=report.report_content
                    )
                except KeyError as e:
                    logger.error(f"Prompt key missing for ReportCheck: {e}")
                    raise HTTPException(status_code=500, detail="Failed to format GPT prompt.")
                
                report_check_prompt = [{"role": "system", "content": report_check_content}]
                report_response = await self.gpt_service.get_response(report_check_prompt, json_format=False)
                logger.info(f"Report is summarized for report ID: {report.id}")

                prompt_session = await self.prompt_repository.find_prompt_session_by_attack_detection_id(report.attack_detection_id)
                if not prompt_session:
                    raise HTTPException(status_code=404, detail="Prompt session not found")
                
                report_check.append(ReportSummary(
                    report_id=report.id,
                    prompt_session_id=prompt_session.id,
                    summary=report_response)
                )

            logger.info(f"Report check generated for user_id: {user_id}")
            return ReportCheckResponseSchema(report_check=report_check)
        except Exception as e:
            logger.error(f"Error processing GPT response for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Error processing report summaries.")

    async def _summarize_logs(self, log_chunks, timestamps):
        """
        각 로그 청크를 요약하고 요약 결과를 반환합니다.
        """
        response_list = []

        for index, (chunk, timestamp) in enumerate(zip(log_chunks, timestamps), start=1):
            log_string = "\n".join(json.dumps(log) for log in chunk)
            daily_insight_content = self.init_prompts["DailyInsight"][0]["content"].format(
                logs=log_string,
                timestamp=timestamp
            )
            daily_insight_prompt = [{"role": "system", "content": daily_insight_content}]

            response = await self.gpt_service.get_response(daily_insight_prompt, json_format=False)
            if response:
                title = f"**{timestamp}에 발생한 공격의 전후로그 분석**"
                response_with_title = f"{title}\n\n{response}"

                response_list.append(response_with_title)
                logger.info(f"Chunk {index} 처리 완료. 응답 추가됨.")
            else:
                logger.warning(f"Chunk {index} 처리 중 응답이 비어 있습니다.")

        return response_list

    def _is_duplicate_log(self, log, seen_logs):
        """필드 비교하여 중복 제외"""
        log_key = (
            log.get("@timestamp"),
            log.get("eventName"),
            log.get("eventID")
        )
        if log_key in seen_logs:
            return True
        return False

    # 공격 10초 전,후 로그 가져오기
    def _fetch_logs_near_attack(self, log):
        timestamp = log.get("@timestamp")
        if not timestamp:
            logger.warning("공격 로그에 타임스탬프가 없습니다. 로그를 건너뜁니다.")
            return None, []

        # 타임스탬프를 UTC 시간으로 변환
        log_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        start_time = (log_time - timedelta(seconds=10)).isoformat()
        end_time = (log_time + timedelta(seconds=10)).isoformat()
        index_name = f"cloudtrail-logs-{log_time.strftime('%Y.%m.%d')}"

        # Elasticsearch 쿼리 생성
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": start_time,
                        "lte": end_time,
                        "format": "strict_date_optional_time"
                    }
                }
            },
            "size": 1000
        }

        # Elasticsearch 쿼리 실행
        try:
            response = self.es.search(index=index_name, body=query)
            related_logs = [hit["_source"] for hit in response["hits"]["hits"]]
            logger.info(f"{timestamp} 기준으로 가져온 관련 로그 개수: {len(related_logs)}")
            return timestamp, related_logs
        except es_exceptions.ConnectionError as e:
            logger.error(f"Elasticsearch 연결 오류: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")
        except es_exceptions.RequestError as e:
            logger.error(f"Elasticsearch 요청 오류: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")
        except Exception as e:
            logger.error(f"Elasticsearch에서 로그를 가져오는 중 오류 발생: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")

    def _fetch_attack_logs(self) -> list:
        # 오늘 날짜 및 1일 전 날짜 계산 (날짜 기준)
        # today = date.today()
        # target_date = today - timedelta(days=1)  # 어제 날짜

        # 시작 및 끝 시간 계산
        # start_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        # end_datetime = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc).date()
        past_day = now - timedelta(days=17)
        past2_day = now - timedelta(days=16)

        # Scroll API 설정
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": past_day.isoformat(),
                        "lte": past2_day.isoformat(),
                        "format": "strict_date_optional_time"
                    }
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}],
            "size": 1000
        }

        try:
            logger.info("cloudtrail-attack-logs 인덱스에서 로그를 가져옵니다...")
            logger.info(f"쿼리 조건 확인: {json.dumps(query, indent=2)}")

            response = self.es.search(index="cloudtrail-attack-logs", body=query, scroll="1m")
            scroll_id = response["_scroll_id"]
            logs = [hit["_source"] for hit in response["hits"]["hits"]]
            logger.info(f"첫 번째 검색 결과 개수: {len(response['hits']['hits'])}")

            while True:
                scroll_response = self.es.scroll(scroll_id=scroll_id, scroll="1m")
                hits = scroll_response["hits"]["hits"]
                if not hits:
                    break
                logs.extend([hit["_source"] for hit in hits])
                logger.info(f"현재까지 가져온 로그 개수: {len(logs)}")

            logger.info(f"총 {len(logs)}개의 공격 로그를 가져왔습니다.")
            return logs

        except es_exceptions.ConnectionError as e:
            logger.error(f"Elasticsearch 연결 오류: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")
        except es_exceptions.RequestError as e:
            logger.error(f"Elasticsearch 요청 오류: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")
        except Exception as e:
            logger.error(f"Elasticsearch에서 로그를 가져오는 중 오류 발생: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Index '{self.es_index}' not found.")

    async def _create_daily_insight(self) -> list:
        try:
            # 1. 공격 로그 가져오기
            attack_logs = self._fetch_attack_logs()
            if not attack_logs:
                logger.error("가져온 로그가 없습니다. 작업을 종료합니다.")
            logger.info(f"가져온 전체 JSON 로그 개수: {len(attack_logs)}")

            seen_logs = set()
            deleted_logs = []

            # 공격 로그를 중복 방지를 위해 seen_logs에 추가
            for log in attack_logs:
                log_key = (
                    log.get("@timestamp"),
                    log.get("eventName"),
                    log.get("eventID")
                )
                seen_logs.add(log_key)

            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_log = {executor.submit(self._fetch_logs_near_attack, log): log for log in attack_logs}
                chunk_timestamps = []  # 청크별 타임스탬프 저장
                final_summaries = []  # 최종 요약 리스트

                for attack_log, future in zip(attack_logs, as_completed(future_to_log)):
                    query_timestamp, related_logs = future.result()

                    if not query_timestamp:
                        logger.info("Skipping log: Missing query timestamp.")
                        continue
                    if not related_logs:
                        logger.info("Skipping log: Missing related logs.")
                        continue
                    logger.info(f"가져온 관련 로그 개수 : {len(related_logs)}")

                    unique_logs = []
                    for log in related_logs:
                        if self._is_duplicate_log(log, seen_logs):
                            deleted_logs.append(log)
                        else:
                            unique_logs.append(log)
                    logger.info(f"삭제된 로그 개수: {len(deleted_logs)}")
                    logger.info(f"가져온 관련 로그 개수 (중복 및 공격 로그 제외 후): {len(unique_logs)}")

                    # 2. 로그를 토큰 한계에 따라 청크로 나누기
                    log_chunks = process_logs_by_token_limit(unique_logs)
                    chunk_timestamps = [query_timestamp] * len(log_chunks)

                    # 3. 청크별 GPT 요청 처리
                    chunk_summaries = await self._summarize_logs(log_chunks, chunk_timestamps) or []  # None이면 빈 리스트로 대체

                    # 4. 응답 리스트를 통합하여 최종 GPT 요청
                    if chunk_summaries:
                        combined_chunk_summary = "\n".join(chunk_summaries)
                        final_content = combined_chunk_summary + f"\n데이터의 관계와 흐름을 파악해서 핵심내용만 간단하게 요약하세요. 결론은 반드시 생략하고 중복되는 내용도 생략합니다. 또한, 반드시 제목은 **{query_timestamp}에 발생한 공격의 전후로그 분석**이라고 해야합니다. 응답은 반드시 markdown 형식을 반환합니다."
                        final_prompt = [{"role": "user", "content": final_content}]

                        final_summary = await self.gpt_service.get_response(final_prompt, json_format=False)
                        logger.info(f"{query_timestamp}에 대한 최종 요약 완료.")
                        final_summaries.append(final_summary)
                
                return final_summaries

        except Exception as e:
            logger.error(f"Error creating daily insight: {e}")
            raise HTTPException(status_code=500, detail="Error creating daily insight.")

    async def get_daily_insight(self, user_id: str) -> DailyInsightResponseSchema:
        try:
            find_dashboard = await self.dashboard_repository.find_dashboard(user_id)
            if find_dashboard and find_dashboard.created_at.date() == date.today():
                logger.info(find_dashboard)
                return DailyInsightResponseSchema(daily_insight=find_dashboard.daily_insight)

            daily_insight = await self._create_daily_insight()
            await self.dashboard_repository.save_dashboard(daily_insight, user_id)
            return DailyInsightResponseSchema(daily_insight=daily_insight)
        except Exception as e:
            logger.error(f"Error processing daily insight for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Error processing daily insight.")
