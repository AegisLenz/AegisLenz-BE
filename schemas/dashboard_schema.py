from pydantic import BaseModel
from typing import List


class AccountByServiceResponseSchema(BaseModel):
    total_service_count: int
    ec2: int
    iam: int
    s3: int
    policy: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_service_count": 14,
                "ec2": 1,
                "iam": 6,
                "s3": 1,
                "policy": 6
            }
        }


class AccountCountResponseSchema(BaseModel):
    users: int
    policies: int
    roles: int
    groups: int

    class Config:
        json_schema_extra = {
            "example": {
                "users": 1,
                "policies": 6,
                "roles": 1,
                "groups": 6
            }
        }


class MonthlyLog(BaseModel):
    month: str
    traffic: int
    attack: int


class DetectionResponseSchema(BaseModel):
    monthly_detection: List[MonthlyLog]
