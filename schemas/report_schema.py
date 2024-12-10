from pydantic import BaseModel


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