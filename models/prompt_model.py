from odmantic import Model, ObjectId, Field
from typing import List, Optional, Dict
from datetime import datetime


class PromptSession(Model):
    user_id: Optional[ObjectId] = None
    chat_summary: Optional[str] = None

    attack_detection_id: Optional[ObjectId] = None
    recommend_history: Optional[List[Dict]] = []
    recommend_questions: Optional[List[str]] = []

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "prompt_sessions"}


class PromptChat(Model):
    prompt_session_id: ObjectId
    role: str  # assistant or user
    content: str
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "prompt_chats"}
