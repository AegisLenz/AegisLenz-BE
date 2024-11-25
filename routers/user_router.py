from fastapi import APIRouter, Depends
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/asset/{user_id}/EC2")
async def get_user_ec2_asset(user_id: str, user_service: UserService = Depends()):
    user_asset = await user_service.get_user_ec2_asset(user_id)
    return user_asset

@router.get("/asset/{user_id}/IAM")
async def get_user_IAM_asset(user_id: str, user_service: UserService = Depends()):
    user_asset = await user_service.get_user_IAM_asset(user_id)
    return user_asset

@router.get("/asset/{user_id}/S3")
async def get_user_S3_asset(user_id: str, user_service: UserService = Depends()):
    user_asset = await user_service.get_user_S3_asset(user_id)
    return user_asset
