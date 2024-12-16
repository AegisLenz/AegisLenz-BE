from odmantic import Model, ObjectId, Field
from typing import Optional, Union
from datetime import datetime


class AttackDetection(Model):
    attack_logs: Union[list, str]
    attack_type: list
    attack_time: datetime
    least_privilege_policy: dict[str, dict[str, list[object]]] = Field(default_factory=dict)
    attack_graph: str
    
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "attack_detections"}


class Report(Model):
    title: Optional[str] = None
    report_content: str

    user_id: str
    report_template_id: Optional[ObjectId] = None
    attack_detection_id: ObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "reports"}


class ReportTemplate(Model):
    title: Optional[str] = None
    selected_field: list[str]
    
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "report_templates"}
