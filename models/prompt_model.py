from odmantic import Model, ObjectId
from typing import List, Optional, Dict
from datetime import datetime


class PromptSession(Model):
    user_id: Optional[ObjectId] = None
    attack_detection_id: Optional[ObjectId] = None
    chat_summary: Optional[str] = None
    recommend_history: Optional[Dict] = {}

    created_at: datetime
    updated_at: datetime

    model_config = {"collection": "prompt_sessions"}


class PromptChat(Model):
    prompt_session_id: ObjectId
    role: str  # assistant or user
    content: str
    recommend_questions: Optional[List[str]]  # role이 user일 때만 데이터가 추가됨
    created_at: datetime

    model_config = {"collection": "prompt_chats"}
