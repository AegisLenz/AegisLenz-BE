from odmantic import Model
from typing import Optional, Dict
from datetime import datetime


class AttackDetection(Model):
    user_id: Optional[str] = None  # foreign key (FK) 역할
    elasticsearch_index_id: Optional[str] = None
    ip_address: Optional[str] = None
    report: str
    least_privilege_policy: Dict
    created_at: datetime

    model_config = {"collection": "attack_detections"}
