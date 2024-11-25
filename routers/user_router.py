from fastapi import APIRouter, Depends
from services import user_service
from database.mongodb_driver import mongodb

router = APIRouter(prefix="/users", tags=["users"])

# 사용자 정보를 MongoDB에 저장하는 API
# @router.get("/")
# async def save_user(user_service: UserService = Depends(), engine=Depends(mongodb.get_engine)):
#     new_user = await user_service.save_user(engine)
#     return new_user

#특정 사용자 정보를 조회하는 API
@router.get("/asset/{user_id}/EC2")
async def get_user_ec2_asset(user_id: str, user_service: user_service = Depends(user_service.UserService), engine=Depends(mongodb.get_engine)):
    user_asset = await user_service.get_user_ec2_asset(user_id, engine)
    return user_asset

@router.get("/asset/{user_id}/IAM")
async def get_user_IAM_asset(user_id: str, user_service: user_service = Depends(user_service.UserService), engine=Depends(mongodb.get_engine)):
    user_asset = await user_service.get_user_IAM_asset(user_id, engine)
    return user_asset

@router.get("/asset/{user_id}/S3")
async def get_user_S3_asset(user_id: str, user_service: user_service = Depends(user_service.UserService), engine=Depends(mongodb.get_engine)):
    user_asset = await user_service.get_user_S3_asset(user_id, engine)
    return user_asset
