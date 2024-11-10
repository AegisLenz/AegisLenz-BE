from fastapi import Depends
from utils.policy.extract_policy_by_cloudTrail import extract_policy_by_cloudTrail
from utils.policy.comparePolicy import comparePolicy
from repositories.user_repository import UserRepository


class PolicyService:
    def __init__(self, user_repository: UserRepository = Depends()):
        self.user_repository = user_repository

    # CloudTrail 로그와 사용자의 AttachedPolicies를 기반으로 최소 권한 정책을 생성
    async def generate_least_privilege_policy(self, log_path: str, user_id: str):
        # 사용자 기존 정책 가져오기
        user_policy = await self.user_repository.get_user_policies(user_id)

        # CloudTrail 로그 기반 최소 권한 정책 생성
        policy_by_cloudTrail = await extract_policy_by_cloudTrail(log_path)

        # 사용자 정책과 최소 권한 정책 비교
        should_remove_action = comparePolicy(user_policy, policy_by_cloudTrail)

        return {
            "original_policy": user_policy,
            "least_privilege_policy": policy_by_cloudTrail,
            "actions_to_remove": list(should_remove_action)
        }
