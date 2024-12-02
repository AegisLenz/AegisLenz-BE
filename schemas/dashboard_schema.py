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