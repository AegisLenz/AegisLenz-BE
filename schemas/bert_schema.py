from pydantic import BaseModel

class PredictionSchema(BaseModel):
    is_attack: bool
    prediction: str

    class Config:
        from_attributes = True  # ORM 모델과 호환되도록 설정