from pydantic import BaseModel
from odmantic import ObjectId, Field
from typing import Optional, Union
from datetime import datetime


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


class PromptSessionSchema(BaseModel):
    prompt_id: ObjectId
    prompt_title: Optional[str]
    prompt_updated_at: datetime


class GetAllPromptResponseSchema(BaseModel):
    prompts: list[PromptSessionSchema]

    class Config:
        json_schema_extra = {
            "example": {
                "prompts": [
                    {
                        "prompt_id": "675827b77f337c71ba90e62a",
                        "prompt_title": "['T1087 - Account Discovery', 'TA0007 - Discovery'] 공격 탐지",
                        "prompt_updated_at": "2024-12-10T20:44:54.261000"
                    }
                ]
            }
        }


class GetPromptContentsSchema(BaseModel):
    role: str  # assistant or user
    content: str


class GetPromptContentsResponseSchema(BaseModel):
    title: Optional[str] = None
    chats: list[GetPromptContentsSchema] = Field(default_factory=list)
    report: Optional[str] = None
    attack_graph: Optional[str] = None
    least_privilege_policy: dict[str, dict[str, list[object]]] = Field(default_factory=dict)
    init_recommend_questions: Optional[list[str]] = Field(default_factory=list)
