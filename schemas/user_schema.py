from pydantic import BaseModel


class BookmarkRequestSchema(BaseModel):
    question: str

    class Config:
        json_schema_extra = {
            "example": {
                "question": "사용자 질문 예시",
            }
        }


class GetAllBookmarkResponseSchema(BaseModel):
    bookmarks: list

    class Config:
        json_schema_extra = {
            "example": {
                "question": "사용자 질문 예시",
            }
        }
