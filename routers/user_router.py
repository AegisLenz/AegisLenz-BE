from fastapi import APIRouter, Depends
from services import user_service
from schemas.user_schema import UserSchema
from models.user_model import User
from core.mongodb_driver import MongoDB

router = APIRouter(prefix="/users", tags=["users"])

mongodb = MongoDB()

# 사용자 정보를 MongoDB에 저장하는 API
@router.get("/")
async def save_user(engine=Depends(mongodb.get_engine)):
    user = User(name="김지윤", age=24, email="jyjyjy7418@gmail.com")
    new_user = await engine.save(user)
    return new_user

# 사용자 정보를 가져오는 API
@router.get("/{user_id}", response_model=UserSchema)
def get_user(user_id: int, user_service=Depends(user_service.UserService)):
    return user_service.get_user_by_id(user_id)