from pydantic import BaseModel
from odmantic import ObjectId, Field
from typing import Optional, Union, List, Dict, Any


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
        json_schema_extra = {
            "example": {
                "prompt_ids": [
                    "507f1f77bcf86cd799439011",
                    "507f191e810c19729de860ea",
                    "507f1f77bcf86cd799439012"
                ]
            }
        }


class GetPromptContentsSchema(BaseModel):
    role: str  # assistant or user
    content: str


class GetPromptContentsResponseSchema(BaseModel):
    title: Optional[str] = None
    chats: List[GetPromptContentsSchema] = Field(default_factory=list)
    report: Optional[str] = None
    attack_graph: Optional[str] = None
    least_privilege_policy: Optional[Dict[str, Dict[str, List[Any]]]] = Field(default_factory=dict)
    init_recommend_questions: Optional[List[str]] = Field(default_factory=list)
