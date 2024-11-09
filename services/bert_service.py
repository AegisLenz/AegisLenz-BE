import os
import openai
from fastapi import HTTPException, Depends
from dotenv import load_dotenv
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
        self.gpt_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.init_prompt = self._load_all_prompts()

    def _load_all_prompts(self):
        prompt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
        prompt_files = {
            "Report": "reportPr.txt",
            "Recommend": "recomm.txt",
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
        report_content = self.init_prompt["Report"][0]["content"].format(
            attack_time=attack_info["attack_time"],
            attack_type=attack_info["attack_type"],
            logs=attack_info["logs"]
        )
        report_prompt = [{"role": "system", "content": report_content}]
        report = await self._receive_gpt_response(report_prompt)
        return report

    async def _create_recommend_questions(self, attack_info, report):
        recommend_content = self.init_prompt["Recommend"][0]["content"].format(
            Tatic=attack_info["attack_type"][0],
            report=report,
            logs=attack_info["logs"]
        )
        recommend_prompt = [{"role": "system", "content": recommend_content}]

        base_query = f"AI 질의 : AWS 환경에서 발생한 공격이 MITRE ATTACK Tatic 중 {attack_info["attack_type"][0]}일 때, 보안 관리자가 어떤 질문을 해야 하는지 추천 질문 만들어줘 "
        prompt_text = f"{base_query}\n 이전과 중복되지 않는 세 줄 질문을 생성해 주세요. 출력은 반드시 세개의 간단한 질문으로만 주세요."
        recommend_prompt.append({"role": "user", "content": prompt_text})

        response = await self._receive_gpt_response(recommend_prompt)
        recommend_questions = [line.strip().strip("\"") for line in response.splitlines() if line.strip()]
        recommend_prompt.append({"role": "assistant", "content": recommend_questions})
        
        return recommend_prompt, recommend_questions

    async def _create_least_privilege_policy(self):
        return {}

    async def predict_attack(self, log_data: str):
        preprocessed_logs = await self.predictor.preprocess_logs(log_data)
        prediction = await self.predictor.predict(preprocessed_logs)
        return prediction

    async def process_after_detection(self, user_id: str, attack_info: dict):
        # 1. 자산 업데이트
        await self.asset_service.update_asset(user_id)

        # 2. 보고서 & 최소권한정책 & 추천 질문 생성
        report = await self._create_report(attack_info)
        recommend_prompt, recommend_questions = await self._create_recommend_questions(attack_info, report)
        least_privilege_policy = await self._create_least_privilege_policy()

        # 3. 프롬프트 생성 및 관련 정보 저장
        attack_detection_id = await self.bert_repository.save_attack_detection(report, least_privilege_policy)

        prompt_session_id = await self.prompt_repository.create_prompt(attack_detection_id, recommend_prompt)
        attack_content = f"{attack_info['attack_type']} 공격이 탐지되었습니다."
        await self.prompt_repository.save_chat(str(prompt_session_id), "assistant", attack_content, recommend_questions)
