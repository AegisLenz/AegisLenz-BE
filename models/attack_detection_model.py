from odmantic import Model, ObjectId
from typing import Optional, Dict, List, Any
from datetime import datetime


class AttackDetection(Model):
    elasticsearch_index_id: Optional[str] = None
    ip_address: Optional[str] = None
    least_privilege_policy: Dict[str, Dict[str, List[Any]]]
    user_id: str
    created_at: datetime

    model_config = {"collection": "attack_detections"}


class Report(Model):
    report_content: str
    user_id: str
    attack_detection_id: ObjectId
    created_at: datetime

    model_config = {"collection": "reports"}
