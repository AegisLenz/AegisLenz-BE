import json
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from core.mongodb_driver import mongodb
from models.attack_detection_model import AttackDetection, SuggestedQuestion

class BertRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client
    
    async def save_attack_detection(self, report, suggested_questions, least_privilege_policy) -> None:
        try:
            suggested_questions = [question if isinstance(question, SuggestedQuestion) else SuggestedQuestion(**question) for question in suggested_questions]
            
            # AttackDetection 객체 생성
            attack_detection = AttackDetection(
                report=report,
                suggested_questions=suggested_questions,
                least_privilege_policy=least_privilege_policy,
                timestamp=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None))
            
            # MongoDB에 저장
            await self.mongodb_engine.save(attack_detection)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")