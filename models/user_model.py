from odmantic import Model
from odmantic.field import Field
from typing import Optional
from datetime import datetime


class User(Model):
    id: str = Field(primary_field=True)  # _id를 임시로 문자열로 설정
    email: str
    
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = None
    openai_api_key: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"collection": "users"}


class Bookmark(Model):
    question: str
    user_id: str

    model_config = {"collection": "bookmarks"}
