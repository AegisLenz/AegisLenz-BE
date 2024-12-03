from pydantic import BaseModel


class AccountByServiceResponseSchema(BaseModel):
    ec2: int
    iam: int
    s3: int
    policy: int

    class Config:
        json_schema_extra = {
            "example": {
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
