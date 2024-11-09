# services/policy_service.py
import os
from policy.extract_policy_by_cloudTrail import extract_policy_by_cloudTrail
from policy.comparePolicy import comparePolicy
from core.mongodb_driver import mongodb
from repositories.user_repository import UserRepository
from policy.common_utils import load_json

# CloudTrail 로그와 사용자의 AttachedPolicies를 기반으로 최소 권한 정책을 생성
async def generate_least_privilege_policy(log_path: str, user_id: str):
    # UserRepository 인스턴스 생성
    user_repository = UserRepository()

    # 사용자 기존 정책 가져오기
    user_policy = await user_repository.get_user_policies(user_id, mongodb.get_engine())

    # CloudTrail 로그 기반 최소 권한 정책 생성
    policy_by_cloudTrail = await extract_policy_by_cloudTrail(log_path)

    # 사용자 정책과 최소 권한 정책 비교
    should_remove_action = comparePolicy(user_policy, policy_by_cloudTrail)

    return {
        "original_policy": user_policy,
        "least_privilege_policy": policy_by_cloudTrail,
        "actions_to_remove": list(should_remove_action)
    }
