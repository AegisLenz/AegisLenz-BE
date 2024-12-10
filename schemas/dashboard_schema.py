from pydantic import BaseModel
from odmantic import ObjectId
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


class ScoreResponseSchema(BaseModel):
    score: float


class RisksResponseSchema(BaseModel):
    inactive_identities: int
    identity_with_excessive_policies: int
    MFA_not_enabled_for_users: int
    MFA_not_enabled_for_root_user: int
    default_security_groups_allow_traffic: int

    class Config:
        json_schema_extra = {
            "example": {
                "inactive_identities": 1,
                "identity_with_excessive_policies": 2,
                "MFA_not_enabled_for_users": 3,
                "MFA_not_enabled_for_root_user": 0,
                "default_security_groups_allow_traffic": 13
            }
        }


class ReportSummary(BaseModel):
    report_id: ObjectId
    summary: str


class ReportCheckResponseSchema(BaseModel):
    report_check: list[ReportSummary]
