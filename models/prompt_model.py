from typing import Optional
from odmantic import Model, ObjectId, Field
from datetime import datetime


class PromptSession(Model):
    title: Optional[str] = Field(default=None)
    recommend_history: Optional[list[dict]] = Field(default_factory=list)
    recommend_questions: Optional[list[str]] = Field(default_factory=list)

    user_id: Optional[str] = Field(default=None)
    attack_detection_id: Optional[ObjectId] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "prompt_sessions"}


class PromptChat(Model):
    role: str
    content: str
    query: Optional[str] = Field(default=None)

    prompt_session_id: ObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "prompt_chats"}
