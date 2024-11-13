from fastapi import APIRouter, Depends
from services.policy_service import PolicyService

router = APIRouter(prefix="/policy", tags=["policy"])

@router.get("/asset/{user_id}/policy")
async def get_least_privilege_policy(user_id: str, policy_service: PolicyService = Depends()):
    return await policy_service.generate_least_privilege_policy(user_id)
