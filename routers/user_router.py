from fastapi import APIRouter, Depends, Body
from odmantic import ObjectId
from services.user_service import UserService
from schemas.user_schema import CreateBookmarkRequestSchema, GetAllBookmarkResponseSchema

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

@router.post("/bookmark")
async def create_bookmark(user_id: str = "1", request: CreateBookmarkRequestSchema = Body(...), user_service: UserService = Depends()):
    return await user_service.create_bookmark(user_id, request.question)

@router.get("/bookmark", response_model=GetAllBookmarkResponseSchema)
async def get_bookmarks(user_id: str = "1", user_service: UserService = Depends()):
    bookmarks = await user_service.get_bookmarks(user_id)
    response = GetAllBookmarkResponseSchema(bookmarks=bookmarks)
    return response

@router.delete("/bookmark/{bookmark_id}")
async def delete_bookmark(bookmark_id: ObjectId, user_service: UserService = Depends()):
    return await user_service.delete_bookmark(bookmark_id)
