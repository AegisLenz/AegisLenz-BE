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
