from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int = None  # 생성될 때 자동으로 추가되는 ID
    name: str
    email: str

    class Config:
        from_attributes = True  # ORM 모델과 호환되도록 설정