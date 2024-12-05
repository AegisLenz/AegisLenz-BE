from odmantic import Model, ObjectId
from typing import List, Optional, Dict
from datetime import datetime


class PromptSession(Model):
    user_id: Optional[ObjectId] = None
    title: Optional[str] = None

    attack_detection_id: Optional[ObjectId] = None
    recommend_history: Optional[List[Dict]] = []
    recommend_questions: Optional[List[str]] = []

    created_at: datetime
    updated_at: datetime

    model_config = {"collection": "prompt_sessions"}


class PromptChat(Model):
    prompt_session_id: ObjectId
    role: str  # assistant or user
    content: str
    created_at: datetime

    model_config = {"collection": "prompt_chats"}
