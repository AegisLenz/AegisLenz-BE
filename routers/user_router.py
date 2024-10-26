from fastapi import APIRouter, Depends
from services.user_service import UserService
from core.mongodb_driver import mongodb

router = APIRouter(prefix="/users", tags=["users"])

# 사용자 정보를 MongoDB에 저장하는 API
@router.get("/")
async def save_user(user_service: UserService = Depends(), engine=Depends(mongodb.get_engine)):
    new_user = await user_service.save_user(engine)
    return new_user