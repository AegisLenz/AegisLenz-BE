from odmantic import EmbeddedModel, Model, ObjectId
from typing import List, Optional
from datetime import datetime


class PromptSession(Model):
    user_id: Optional[str] = None  # foreign key (FK) 역할
    chat_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"collection": "PromptSession"}


class Message(EmbeddedModel):
    timestamp: datetime
    role: str
    content: Optional[str] = None


class PromptMessage(Model):
    prompt_session_id: ObjectId
    messages: List[Message]

    model_config = {"collection": "PromptMessage"}