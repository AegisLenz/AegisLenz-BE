from odmantic import EmbeddedModel, Model
from typing import List, Union


class PolicyAction(EmbeddedModel):
    Action: List[str]  # 허용된 액션 목록
    Effect: str  # Allow or Deny
    Resource: Union[str, List[str]]  # 리소스 ARN 패턴


class Policy(Model):
    service: str
    event_name: str
    policy: List[PolicyAction]

    model_config = {"collection": "policies"}