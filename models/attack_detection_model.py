from odmantic import Model
from odmantic.field import Field
from typing import Optional
from datetime import datetime


class AttackDetection(Model):
    elasticsearch_index_id: Optional[str] = None
    ip_address: Optional[str] = None
    report: str
    least_privilege_policy: dict[str, dict[str, list[object]]] = Field(default_factory=dict)
    attack_graph: str

    user_id: str
    created_at: datetime

    model_config = {"collection": "attack_detections"}
