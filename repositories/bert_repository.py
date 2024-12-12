from fastapi import HTTPException
from odmantic import ObjectId
from datetime import datetime, timedelta, timezone
from database.mongodb_driver import mongodb
from models.attack_detection_model import AttackDetection, Report


class BertRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client
    
    async def save_attack_detection(self, report: str, least_privilege_policy: dict[str, dict[str, list[object]]], attack_graph: str, user_id: str) -> str:
        try:
            if not user_id or not isinstance(user_id, str):
                raise ValueError("Invalid user_id")
            if not attack_graph or not isinstance(attack_graph, str):
                raise ValueError("Invalid attack_graph")

            attack_detection = AttackDetection(
                least_privilege_policy=least_privilege_policy,
                attack_graph=attack_graph,
                user_id=user_id,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )

            report = Report(
                report_content=report,
                user_id=user_id,
                attack_detection_id=attack_detection.id,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            
            await self.mongodb_engine.save(attack_detection)
            await self.mongodb_engine.save(report)

            return attack_detection.id

        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save attack detection: {e}")

    async def find_attack_detection(self, attack_detection_id: str) -> str:
        try:
            if not attack_detection_id or not ObjectId.is_valid(attack_detection_id):
                raise ValueError("Invalid attack_detection_id.")

            attack_detection = await self.mongodb_engine.find_one(
                AttackDetection,
                AttackDetection.id == ObjectId(attack_detection_id)
            )
            return attack_detection
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")