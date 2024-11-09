# BERT 예측 결과를 위한 데이터 구조를 정의하는 파일
from pydantic import BaseModel

class PredictionSchema(BaseModel):
    is_attack: bool
    prediction: str

    class Config:
        from_attributes = True  # ORM 모델과 호환되도록 설정