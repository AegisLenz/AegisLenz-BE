from fastapi import HTTPException
from odmantic import ObjectId
from datetime import datetime, timedelta, timezone
from database.mongodb_driver import mongodb
from models.attack_detection_model import AttackDetection


class BertRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client
    
    async def save_attack_detection(self, report: str, least_privilege_policy: dict[str, dict[str, list[object]]], attack_graph: str, user_id: str) -> str:
        try:
            # AttackDetection 객체 생성
            attack_detection = AttackDetection(
                report=report,
                least_privilege_policy=least_privilege_policy,
                attack_graph=attack_graph,
                user_id=user_id,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            
            await self.mongodb_engine.save(attack_detection)
            return attack_detection.id
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    async def find_attack_detection(self, attack_detaction_id: str) -> str:
        try:
            attack_detection = await self.mongodb_engine.find_one(
                AttackDetection,
                AttackDetection.id == ObjectId(attack_detaction_id)
            )
            return attack_detection
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")
