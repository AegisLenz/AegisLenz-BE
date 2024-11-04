import os
import openai
from fastapi import HTTPException, Depends
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from ai.predict import BERTPredictor
from services.asset_service import AssetService
from services.prompt_service import PromptService
from repositories.prompt_repository import PromptRepository
from repositories.bert_repository import BertRepository

class BERTService:
    def __init__(self, bert_repository: BertRepository = Depends(), prompt_repository: PromptRepository = Depends(), asset_service: AssetService = Depends(), prompt_service: PromptService = Depends()):
        self.predictor = BERTPredictor()
        self.asset_service = asset_service
        self.prompt_service = prompt_service
        self.bert_repository = bert_repository
        self.prompt_repository = prompt_repository
        
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.gpt_client = openai.OpenAI(api_key=self.api_key)
        self.init_prompt = self._load_all_prompts()

    def _load_all_prompts(self):
        prompt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
        prompt_files = {
            "Report": "reportPr.txt",
        }

        init_prompt = {}
        for name, file_name in prompt_files.items():
            path = os.path.join(prompt_dir, file_name)
            init_prompt[name] = [{"role": "system", "content": self._read_prompt(path)}]
        return init_prompt
    
    def _read_prompt(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail=f"Prompt file not found: {file_path}")

    async def predict_attack(self, log_data: str):
        preprocessed_logs = await self.predictor.preprocess_logs(log_data)
        prediction = await self.predictor.predict(preprocessed_logs)
        return prediction

    def _clean_response(self, response):
        choices = getattr(response, "choices", [])
        return choices[0].message.content if choices and hasattr(choices[0].message, 'content') else None

    async def _receive_gpt_response(self, init_prompt):
        response = self.gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=init_prompt
        )
        return self._clean_response(response)

    async def _create_report(self, attack_info):
        # 동적 값을 삽입하여 최종 프롬프트 구성
        report_content = self.init_prompt["Report"][0]["content"].format(
            attack_time=attack_info["attack_time"],
            attack_type=attack_info["attack_type"],
            logs=attack_info["logs"]
        )
        report_prompt = [{"role": "system", "content": report_content}]
        report = await self._receive_gpt_response(report_prompt)
        return report

    async def _create_suggested_questions(self, report):
        return []

    async def _create_least_privilege_policy(self):
        return {}

    async def process_tasks_after_detection(self, user_id: str, attack_info: dict):
        # 1. 자산 업데이트
        await self.asset_service.update_asset(user_id)

        # 2. 새 프롬프트 세션 생성
        prompt_session_id = await self.prompt_repository.create_prompt()

        # 3. 프롬프트 공격 알림 내용 생성
        attack_content = f"{attack_info['attack_type']} 공격이 탐지되었습니다."
        attack_history = [{"role": "assistant", "content": attack_content, "timestamp": datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()}]
        await self.prompt_repository.save_conversation_history(str(prompt_session_id), attack_history)

        # 4. 보고서 & 최소권한정책 & 추천 질문 생성
        report = await self._create_report(attack_info)
        suggested_questions = await self._create_suggested_questions(report)
        least_privilege_policy = await self._create_least_privilege_policy()

        await self.bert_repository.save_attack_detection(report, suggested_questions, least_privilege_policy)