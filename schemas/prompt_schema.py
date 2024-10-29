from pydantic import BaseModel
from odmantic import ObjectId
from typing import Optional, Union

class PromptChatRequestSchema(BaseModel):
    user_input: str  # 사용자 요청 메시지

    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "사용자 질문 예시",
            }
        }

class PromptChatStreamResponseSchema(BaseModel):
    status: str  # "processing" 또는 "complete" 상태를 나타냄
    type: Optional[str] = None
    data: Optional[Union[str, list]] = None  # ChatGPT로부터 받은 응답 데이터

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "type": "ElasticSearch",
                "data": "ChatGPT 응답 예시"
            }
        }

class CreatePromptResponseSchema(BaseModel):
    prompt_id: ObjectId

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_id": "1",
            }
        }