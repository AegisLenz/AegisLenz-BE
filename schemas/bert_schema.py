from pydantic import BaseModel

class PredictionSchema(BaseModel):
    is_attack: bool
    prediction: str

    class Config:
        from_attributes = True