from odmantic import EmbeddedModel, Model, ObjectId
from typing import List, Optional
from datetime import datetime


class PromptSession(Model):
    user_id: Optional[ObjectId] = None
    attack_detection_id: Optional[ObjectId] = None
    chat_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"collection": "prompt_sessions"}


class History(EmbeddedModel):
    role: str
    content: str


class PromptHistory(Model):
    prompt_session_id: ObjectId
    persona: str
    history: List[History]

    model_config = {"collection": "prompt_sessions"}


class PromptChat(Model):
    prompt_session_id: ObjectId
    role: str  # assistant or user
    content: str
    created_at: datetime


# class Message(EmbeddedModel):
#     created_at: datetime
#     role: str
#     content: str

# class PromptMessage(Model):
#     prompt_session_id: ObjectId
#     messages: List[Message]
#     histories: List[PersonaHistory]

#     model_config = {"collection": "prompt_messages"}