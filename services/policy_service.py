from fastapi import Depends, HTTPException
from services.policy.extract_policy_by_cloudTrail import extract_policy_by_cloudTrail
from services.policy.comparePolicy import clustered_compare_policy
from repositories.user_repository import UserRepository
from common.logging import setup_logger

logger = setup_logger()


class PolicyService:
    def __init__(self, user_repository: UserRepository = Depends()):
        self.user_repository = user_repository

    async def generate_least_privilege_policy(self, user_id: str) -> dict:
        # 1. 사용자 기존 정책 가져오기
        try:
            user_policy = await self.user_repository.get_user_policies(user_id)
            logger.debug(f"Retrieved user policies for user_id {user_id}: {user_policy}")
        except Exception as e:
            logger.error(f"Error retrieving user policies for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve user policies.")

        # 2. CloudTrail 로그 기반 최소 권한 정책 생성
        try:
            clustered_policy_by_cloudtrail = extract_policy_by_cloudTrail()
            logger.debug(f"Generated clustered policy from CloudTrail logs: {clustered_policy_by_cloudtrail}")
        except Exception as e:
            logger.error(f"Error generating policy from CloudTrail logs: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate policy from CloudTrail logs.")

        # 3. 사용자 정책과 최소 권한 정책 비교
        try:
            should_remove_action = clustered_compare_policy(user_policy, clustered_policy_by_cloudtrail)
            logger.debug(f"Actions to remove after comparing policies: {should_remove_action}")
            converted_actions = {k: [list(v) for v in val] for k, val in should_remove_action.items()}
        except Exception as e:
            logger.error(f"Error comparing policies for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to compare policies.")

        # 반환값 구성
        result = {
            "original_policy": user_policy,
            "least_privilege_policy": clustered_policy_by_cloudtrail,
            "actions_to_remove": converted_actions
        }
        logger.debug(f"Successfully generated least privilege policy result for user_id {user_id}.")
        return result
