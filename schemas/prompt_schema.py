from pydantic import BaseModel
from typing import Optional

class PromptChatRequestSchema(BaseModel):
    user_input: str # 사용자 요청 메시지

    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "사용자 질문 예시",
            }
        }

class PromptChatStreamResponseSchema(BaseModel):
    status: str  # "processing" 또는 "complete" 상태를 나타냄
    type: Optional[str] = None
    data: str    # ChatGPT로부터 받은 응답 데이터

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "type": "ElasticSearch",
                "data": "ChatGPT 응답 예시"
            }
        }