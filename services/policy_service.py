from fastapi import Depends
from utils.policy.extract_policy_by_cloudTrail import extract_policy_by_cloudTrail
from utils.policy.comparePolicy import clustered_compare_policy
from repositories.user_repository import UserRepository


class PolicyService:
    def __init__(self, user_repository: UserRepository = Depends()):
        self.user_repository = user_repository

    async def generate_least_privilege_policy(self, user_id: str) -> dict:
        # 1. 사용자 기존 정책 가져오기
        user_policy = await self.user_repository.get_user_policies(user_id)

        # 2. CloudTrail 로그 기반 최소 권한 정책 생성
        clustered_policy_by_cloudtrail = extract_policy_by_cloudTrail()

        # 3. 사용자 정책과 최소 권한 정책 비교
        should_remove_action = clustered_compare_policy(user_policy, clustered_policy_by_cloudtrail)
        converted_actions = {k: [list(v) for v in val] for k, val in should_remove_action.items()}

        return {
            "original_policy": user_policy,
            "least_privilege_policy": clustered_policy_by_cloudtrail,
            "actions_to_remove": converted_actions
        }
