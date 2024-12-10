from odmantic import Model, ObjectId, Field
from typing import Optional
from datetime import datetime


class AttackDetection(Model):
    elasticsearch_index_id: Optional[str] = None
    source_ip: Optional[str] = None
    least_privilege_policy: dict[str, dict[str, list[object]]] = Field(default_factory=dict)
    attack_graph: str
    
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "attack_detections"}


class Report(Model):
    report_content: str
    title: Optional[str] = None

    user_id: str
    attack_detection_id: ObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "reports"}


class ReportTemplate(Model):
    title: Optional[str] = None
    selected_field: list
    prompt_text: str
    
    user_id: str
    report_id: Optional[ObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"collection": "report_templates"}
