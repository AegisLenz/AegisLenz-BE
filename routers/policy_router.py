# routers/policy_router.py
from fastapi import APIRouter, Depends
from services.policy_service import generate_least_privilege_policy
import os

router = APIRouter(prefix="/policy", tags=["policy"])

# CloudTrail 로그와 사용자 정책을 기반으로 최소 권한 정책을 생성합니다.
@router.get("/asset/{user_id}/policy")
async def get_least_privilege_policy(user_id: str):
    # 환경 변수에서 정책을 생성할 로그 경로 가져오기 -> 이 부분 ES에서 가져오는 걸로 바꿔야하는데.. 
    log_path = os.getenv("LOG_PATH")

    # 최소 권한 정책 생성 서비스 호출
    result = await generate_least_privilege_policy(log_path, user_id)
    return result
