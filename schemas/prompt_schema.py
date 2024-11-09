# 프롬프트 세션과 대화 스트림의 요청과 응답 형식을 정의
from pydantic import BaseModel
from odmantic import ObjectId
from typing import Optional, Union, List

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
    prompt_session_id: ObjectId

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_session_id": "1",
            }
        }

class GetAllPromptResponseSchema(BaseModel):
    prompt_ids: List[str]

    class Config:
        schema_extra = {
            "example": {
                "prompt_ids": [
                    "507f1f77bcf86cd799439011",
                    "507f191e810c19729de860ea",
                    "507f1f77bcf86cd799439012"
                ]
            }
        }