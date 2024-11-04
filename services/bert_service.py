import os
import openai
from fastapi import Depends
from dotenv import load_dotenv
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
        
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.gpt_client = openai.OpenAI(api_key=self.api_key)

    async def predict_attack(self, log_data: str):
        preprocessed_logs = await self.predictor.preprocess_logs(log_data)
        prediction = await self.predictor.predict(preprocessed_logs)
        return prediction

    async def process_tasks_after_detection(self, user_id: str, attack_info: dict):
        # 1. 자산 업데이트
        # await self.asset_service.update_asset(user_id)

        # 2. 새 프롬프트 세션 생성
        prompt_session_id = await self.prompt_repository.create_prompt()

        # 3. 프롬프트 공격 알림 내용 생성
        attack_content = f"{attack_info['technique']} 공격이 탐지되었습니다."
        attack_history = [{"role": "assistant", "content": attack_content, "timestamp": datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()}]
        await self.prompt_repository.save_conversation_history(str(prompt_session_id), attack_history)

        # 4. 보고서 & 최소권한정책 & 추천 질문 생성
