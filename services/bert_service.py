from fastapi import Depends
from ai.predict import BERTPredictor
from services.gpt_service import GPTService
from services.asset_service import AssetService
from services.policy_service import PolicyService
from repositories.prompt_repository import PromptRepository
from repositories.bert_repository import BertRepository


class BERTService:
    def __init__(self, bert_repository: BertRepository = Depends(), prompt_repository: PromptRepository = Depends(),
                 asset_service: AssetService = Depends(), gpt_service: GPTService = Depends(), policy_service: PolicyService = Depends()):
        self.predictor = BERTPredictor()
        self.asset_service = asset_service
        self.gpt_service = gpt_service
        self.policy_service = policy_service
        self.bert_repository = bert_repository
        self.prompt_repository = prompt_repository
        self.init_prompts = self.gpt_service._load_prompts()

    async def _create_report(self, attack_info):
        report_content = self.init_prompts["Report"][0]["content"].format(
            attack_time=attack_info["attack_time"],
            attack_type=attack_info["attack_type"],
            logs=attack_info["logs"]
        )
        report_prompt = [{"role": "system", "content": report_content}]
        report = await self.gpt_service.get_response(report_prompt, json_format=False)
        return report

    async def _create_recommend_questions(self, attack_info: dict, report: str):
        recommend_content = self.init_prompts["Recommend"][0]["content"].format(
            attack_type=attack_info["attack_type"][0],
            report=report,
            logs=attack_info["logs"]
        )
        recommend_prompt = [{"role": "system", "content": recommend_content}]

        base_query = f"AI 질의 : AWS 환경에서 발생한 공격이 MITRE ATTACK Tatic 중 {attack_info["attack_type"][0]}일 때, 보안 관리자가 어떤 질문을 해야 하는지 추천 질문 만들어줘 "
        recommend_prompt.append({"role": "user", "content": base_query})

        response = await self.gpt_service.get_response(recommend_prompt, json_format=False, recomm=True)
        recommend_questions = [line.strip().strip("\"") for line in response.splitlines() if line.strip()]
        recommend_prompt.append({"role": "assistant", "content": "\n".join(recommend_questions)})
        return recommend_prompt, recommend_questions

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
        least_privilege_policy = await self.policy_service.generate_least_privilege_policy(user_id)

        # 3. 프롬프트 생성 및 관련 정보 저장
        attack_detection_id = await self.bert_repository.save_attack_detection(report, least_privilege_policy)

        prompt_session_id = await self.prompt_repository.create_prompt(attack_detection_id, recommend_prompt, recommend_questions)
        attack_content = f"{attack_info['attack_type']} 공격이 탐지되었습니다."
        await self.prompt_repository.save_chat(str(prompt_session_id), "assistant", attack_content)
        return prompt_session_id
