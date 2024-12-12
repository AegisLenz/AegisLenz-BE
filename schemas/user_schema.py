from pydantic import BaseModel


class CreateBookmarkRequestSchema(BaseModel):
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
                "bookmarks": [
                    "사용자 질문 예시1",
                    "사용자 질문 예시2",
                    "사용자 질문 예시3"
                ]
            }
        }
