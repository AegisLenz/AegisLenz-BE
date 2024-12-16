from fastapi import Depends, HTTPException
from services.policy.extract_policy_by_cloudTrail import extract_policy_by_cloudTrail
from services.policy.comparePolicy import clustered_compare_policy
from services.policy.filter_original_policy import filter_original_policy
from repositories.user_repository import UserRepository
from common.logging import setup_logger
from services.policy.common_utils import convert_list_to_dict
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
            
            # None 체크
            if clustered_policy_by_cloudtrail is None:
                logger.error("clustered_policy_by_cloudtrail is None. It must be a dictionary.")
                raise ValueError("clustered_policy_by_cloudtrail is None. It must be a dictionary.")
            
            # 리스트일 경우 딕셔너리로 변환
            if isinstance(clustered_policy_by_cloudtrail, list):
                logger.debug(f"Converting list to dictionary for clustered_policy_by_cloudtrail: {clustered_policy_by_cloudtrail}")
                clustered_policy_by_cloudtrail = convert_list_to_dict(clustered_policy_by_cloudtrail)
            
            # 타입 체크
            if not isinstance(clustered_policy_by_cloudtrail, dict):
                logger.error(f"Invalid type for clustered_policy_by_cloudtrail: {type(clustered_policy_by_cloudtrail)}")
                raise TypeError("clustered_policy_by_cloudtrail must be a dictionary.")

            # 디버깅 로그 추가
            logger.debug(f"Type of clustered_policy_by_cloudtrail: {type(clustered_policy_by_cloudtrail)}")
            logger.debug(f"clustered_policy_by_cloudtrail: {clustered_policy_by_cloudtrail}")
            
            # 사용자 정책과 최소 권한 정책 비교
            should_remove_action = clustered_compare_policy(user_policy, clustered_policy_by_cloudtrail)
            
            logger.debug(f"Actions to remove after comparing policies: {should_remove_action}")
            
            # converted_actions에서 v가 None일 때도 빈 리스트로 변환하도록 개선
            converted_actions = {k: [list(v) if v else [] for v in val] for k, val in should_remove_action.items()}

        except Exception as e:
            # 스택 트레이스를 출력하고 구체적인 에러 메시지를 포함
            logger.error(f"Error comparing policies for user_id {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to compare policies: {str(e)}")
        
        
        result = {
            "original_policy": user_policy,
            "least_privilege_policy": clustered_policy_by_cloudtrail,
            "actions_to_remove": converted_actions
        }
        logger.debug(f"Successfully generated least privilege policy result for user_id {user_id}.")
        return result
