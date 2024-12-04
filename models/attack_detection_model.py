from odmantic import Model
from typing import Optional, Dict, List, Any
from datetime import datetime


class AttackDetection(Model):
    user_id: Optional[str] = None
    elasticsearch_index_id: Optional[str] = None
    ip_address: Optional[str] = None
    report: str
    least_privilege_policy: Dict[str, Dict[str, List[Any]]]
    created_at: datetime

    model_config = {"collection": "attack_detections"}


class Report(Model):
    report_id: Optional[str]
    report_string: str

    model_config = {"collection": "reports"}
