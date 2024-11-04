from odmantic import EmbeddedModel, Model
from typing import List, Optional, Dict
from datetime import datetime


class SuggestedQuestion(EmbeddedModel):
    question: str


class AttackDetection(Model):
    user_id: Optional[str] = None  # foreign key (FK) 역할
    elasticsearch_index_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime
     
    report: str
    least_privilege_policy: Dict
    suggested_questions: List[SuggestedQuestion]

    model_config = {"collection": "attack_detections"}