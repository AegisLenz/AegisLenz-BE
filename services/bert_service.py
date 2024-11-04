import json
from fastapi import Depends
from datetime import datetime, timedelta, timezone
from ai.predict import BERTPredictor
from services.asset_service import AssetService
from services.prompt_service import PromptService
from repositories.prompt_repository import PromptRepository

class BERTService:
    def __init__(self, prompt_repository: PromptRepository = Depends(), asset_service: AssetService = Depends(), prompt_service: PromptService = Depends()):
        self.predictor = BERTPredictor()
        self.asset_service = asset_service
        self.prompt_service = prompt_service
        self.prompt_repository = prompt_repository

    async def predict_attack(self, log_data: str):
        preprocessed_logs = await self.predictor.preprocess_logs(log_data)
        prediction = await self.predictor.predict(preprocessed_logs)
        return prediction

    async def process_tasks_after_detection(self, user_id):
        # 1. 자산 업데이트
        await self.asset_service.update_asset(user_id)

        # 2. 새 프롬프트 세션 생성
       

        # 3. 프롬프트 공격 알림 내용 생성


        # 4. 보고서 & 최소권한정책 & 추천 질문 생성