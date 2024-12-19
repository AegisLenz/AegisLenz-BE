from pydantic import BaseModel
from odmantic import ObjectId


class CreateBookmarkRequestSchema(BaseModel):
    question: str

    class Config:
        json_schema_extra = {
            "example": {
                "question": "사용자 질문 예시",
            }
        }


class BookmarkSchema(BaseModel):
    bookmark_id: ObjectId
    question: str


class GetAllBookmarkResponseSchema(BaseModel):
    bookmarks: list[BookmarkSchema]

    class Config:
        json_schema_extra = {
            "example": {
                "bookmarks": [
                    {
                        "bookmark_id": "675ae4a99b177f9da358032d",
                        "question": "사용자 질문 예시"
                    }
                ]
            }
        }


class LoginFormSchema(BaseModel):
    user_name: str
    user_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "example_user",
                "user_password": "example_password"
            }
        }

 
class CreateAccountFormSchema(BaseModel):
    user_name: str
    user_password: str
    email: str
    AWS_PUBLIC_KEY: str
    AWS_PRIVATE_KEY: str
    CHAT_GPT_TOKEN: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "example_user",
                "user_password": "example_password",
                "email": "example@example.com",
                "AWS_PUBLIC_KEY": "example_public_key",
                "AWS_PRIVATE_KEY": "example_private_key",
                "CHAT_GPT_TOKEN": "example_token"
            }
        }
