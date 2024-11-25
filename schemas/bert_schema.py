from pydantic import BaseModel


class PredictionSchema(BaseModel):
    is_attack: bool
    technique: str
    tactic: str
    prompt_session_id: str

    class Config:
        from_attributes = True