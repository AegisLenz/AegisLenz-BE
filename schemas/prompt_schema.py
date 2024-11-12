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
    chats: List[GetPromptContentsSchema]
    report: Optional[str]
    init_recommend_questions: Optional[List[str]]

    class Config:
        schema_extra = {
            "example": {
                "chats": [
                    {"role": "user", "content": "자산 보여줘"},
                    {"role": "assistant", "content": "자산 정보입니다"},
                    {"role": "user", "content": "감사합니다"}
                ],
                "report": "Example report data",
                "init_recommend_questions": [
                    "지난 일주일 동안 접속한 모든 IAM 계정의 목록을 제공해주세요.",
                    "각 IAM 계정이 로그인한 정확한 시간과 날짜를 포함하여 보여주세요.",
                    "해당 기간 동안 가장 많이 접속한 IAM 계정을 확인할 수 있는 방법을 설명해주세요."
                ]
            }
        }