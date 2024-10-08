from fastapi import APIRouter, Depends
from services import user_service
from schemas.user_schema import UserSchema

router = APIRouter(prefix="/users", tags=["users"])

# 사용자 정보를 가져오는 API
@router.get("/{user_id}", response_model=UserSchema)
def get_user(user_id: int, user_service=Depends(user_service.UserService)):
    return user_service.get_user_by_id(user_id)