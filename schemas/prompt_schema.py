from pydantic import BaseModel
from odmantic import ObjectId
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
    title: str
    chats: List[GetPromptContentsSchema]
    report: Optional[str]
    attack_graph: Optional[str]
    least_privilege_policy: Optional[Dict[str, Dict[str, List[Any]]]]
    init_recommend_questions: Optional[List[str]]

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Title",
                "chats": [
                    {"role": "user", "content": "최근에 변경된 자산 정보를 보여주세요."},
                    {"role": "assistant", "content": "여기 최근 자산 변경 내역입니다."},
                    {"role": "user", "content": "감사합니다, 추가 권한 정책도 볼 수 있을까요?"}
                ],
                "report": "최근 계정 활동 분석에 대한 보고서 데이터입니다.",
                "least_privilege_policy": {
                    "Jiyun_Kim": {
                        "PolicyA": ["s3:ListBuckets", "s3:GetObject"],
                        "PolicyB": ["ec2:StartInstances"]
                    },
                    "Hyunjun_Park": {
                        "PolicyA": ["s3:ListBuckets"],
                        "PolicyC": ["ec2:DescribeInstances", "sqs:ReceiveMessage"]
                    }
                },
                "init_recommend_questions": [
                    "최근 30일간 EC2 인스턴스 상태 변경 내역을 보여주세요.",
                    "S3 버킷에 접근한 IAM 사용자의 목록을 시간별로 제공해주세요.",
                    "IAM 계정 중 최근 비밀번호 변경 내역이 있는 계정을 확인해주세요."
                ]
            }
        }