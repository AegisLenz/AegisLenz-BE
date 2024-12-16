from pydantic import BaseModel
from odmantic import ObjectId
from typing import Optional
from datetime import datetime


class GetAllReportResponseSchema(BaseModel):
    report_ids: list[str]

    class Config:
        json_schema_extra = {
            "example": {
                "report_ids": [
                    "507f1f77bcf86cd799439011",
                    "507f191e810c19729de860ea",
                    "507f1f77bcf86cd799439012"
                ]
            }
        }


class GetReportResponseSchema(BaseModel):
    title: Optional[str] = None
    report_content: str
    report_id: ObjectId
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Title",
                "report_content": "# 공격 탐지 보고서\n\n## 공격 탐지 시간\n- **2024-12-10T20:35:52.619217**\n\n",
                "report_id": "675827b77f337c71ba90e629",
                "created_at": "2024-12-10T20:36:23.982000"
            }
        }


class CreateReportTemplateRequestSchema(BaseModel):
    title: Optional[str] = None
    selected_field: list

    class Config:
        json_schema_extra = {
            "example": {
                "title": "string",
                "selected_field": [
                    "string"
                ]
            }
        }


class GetAllReportTemplateResponseSchema(BaseModel):
    report_template_ids: list[str]

    class Config:
        json_schema_extra = {
            "example": {
                "report_template_ids": [
                    "507f1f77bcf86cd799439011",
                    "507f191e810c19729de860ea",
                    "507f1f77bcf86cd799439012"
                ]
            }
        }


class GetReportTemplateResponseSchema(BaseModel):
    title: Optional[str] = None
    selected_field: list[str]
    created_at: datetime
