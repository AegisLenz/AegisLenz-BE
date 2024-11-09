from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from core.mongodb_driver import mongodb
from models.attack_detection_model import AttackDetection


class BertRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client
    
    async def save_attack_detection(self, report: str, least_privilege_policy: list) -> None:
        try:           
            # AttackDetection 객체 생성
            attack_detection = AttackDetection(
                report=report,
                least_privilege_policy=least_privilege_policy,
                timestamp=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            
            # MongoDB에 저장
            await self.mongodb_engine.save(attack_detection)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")