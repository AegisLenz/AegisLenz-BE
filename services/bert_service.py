import asyncio
from fastapi import Depends, HTTPException
from ai.predict import BERTPredictor
from services.gpt_service import GPTService
from services.asset_service import AssetService
from services.policy_service import PolicyService
from repositories.prompt_repository import PromptRepository
from repositories.bert_repository import BertRepository
from common.logging import setup_logger

logger = setup_logger()


class BERTService:
    def __init__(self, bert_repository: BertRepository = Depends(), prompt_repository: PromptRepository = Depends(),
                 asset_service: AssetService = Depends(), gpt_service: GPTService = Depends(), policy_service: PolicyService = Depends()):
        self.predictor = BERTPredictor()
        self.asset_service = asset_service
        self.gpt_service = gpt_service
        self.policy_service = policy_service
        self.bert_repository = bert_repository
        self.prompt_repository = prompt_repository

        try:
            self.init_prompts = self.gpt_service._load_prompts()
            logger.debug("Successfully loaded initial prompts.")
        except Exception as e:
            logger.error(f"Failed to load initial prompts: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize prompts.")

    async def _create_report(self, attack_info):
        try:
            report_content = self.init_prompts["InitReport"][0]["content"].format(
                attack_time=attack_info["attack_time"],
                attack_type=attack_info["attack_type"],
                logs=attack_info["logs"]
            )
            report_prompt = [{"role": "system", "content": report_content}]
            report = await self.gpt_service.get_response(report_prompt, json_format=False)
            return report
        except Exception as e:
            logger.error(f"Error while creating report: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate attack report.")

    async def _create_recommend_questions(self, attack_info: dict, report: str):
        try:
            recommend_content = self.init_prompts["Recommend"][0]["content"].format(
                attack_type=attack_info["attack_type"][0],
                report=report,
                logs=attack_info["logs"]
            )
            recommend_prompt = [{"role": "system", "content": recommend_content}]

            base_query = f"AI 질의 : AWS 환경에서 발생한 공격이 MITRE ATTACK Tatic 중 {attack_info["attack_type"][0]}일 때, 보안 관리자가 어떤 질문을 해야 하는지 추천 질문 만들어줘"
            recommend_prompt.append({"role": "user", "content": base_query})
            response = await self.gpt_service.get_async_response(recommend_prompt, json_format=False, recomm=True)
            
            recommend_questions = [line.strip().strip("\"") for line in response.splitlines() if line.strip()]
            recommend_prompt.append({"role": "assistant", "content": "\n".join(recommend_questions)})
            return recommend_prompt, recommend_questions
        except Exception as e:
            logger.error(f"Error while creating recommended questions: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate recommended questions.")

    async def _create_attack_graph(self, attack_info: dict):
        try:
            attack_graph_content = self.init_prompts["Graph"][0]["content"].format(
                logs=attack_info["logs"]
            )
            attack_graph_prompt = [{"role": "system", "content": attack_graph_content}]
            attack_graph = await self.gpt_service.get_async_response(attack_graph_prompt, json_format=False)
            return attack_graph
        except Exception as e:
            logger.error(f"Error while creating attack graph: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate attack graph.")

    async def predict_attack(self, log_data: str):
        try:
            preprocessed_logs = await self.predictor.preprocess_logs(log_data)
            prediction = await self.predictor.predict(preprocessed_logs)
            return prediction
        except Exception as e:
            logger.error(f"Error during attack prediction: {e}")
            raise HTTPException(status_code=500, detail="Failed to predict attack.")

    async def process_after_detection(self, user_id: str, attack_info: dict):
        # 1. 자산 업데이트
        try:
            await self.asset_service.update_asset(user_id)
            logger.debug("asset updated successfully.")
        except Exception as e:
            logger.error(f"Error updating asset for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update user assets.")

        # 2. 보고서 & 추천 질문 & 최소권한정책 & 공격 흐름그래프 생성
        try:
            report = await self._create_report(attack_info)
            logger.debug(f"Generated report: {report}")

            (recommend_prompt, recommend_questions), least_privilege_policy, attack_graph = await asyncio.gather(
                self._create_recommend_questions(attack_info, report),
                self.policy_service.generate_least_privilege_policy(user_id),
                self._create_attack_graph(attack_info)
            )
            logger.debug("report, recommend questions, least privilege policy, attack_graph generated successfully.")
        except Exception as e:
            logger.error(f"Error during report or questions or policies or graph generation: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate report, questions, policies, or graph.")

        # 3. 프롬프트 생성 및 공격 관련 정보 저장
        try:
            title = f"{attack_info['attack_type']} 공격 탐지"
            attack_content = f"{attack_info["attack_time"]}에 {attack_info['attack_type']} 공격이 탐지되었습니다."

            attack_detection_id = await self.bert_repository.save_attack_detection(report, least_privilege_policy, attack_graph, user_id, attack_info)
            prompt_session_id = await self.prompt_repository.create_prompt(user_id, attack_detection_id, recommend_prompt, recommend_questions, title)
            await self.prompt_repository.save_chat(str(prompt_session_id), "assistant", attack_content)
            
            logger.debug("attack detection and prompt session saved successfully.")
            return prompt_session_id
        except Exception as e:
            logger.error(f"Error saving attack detection or prompts: {e}")
            raise HTTPException(status_code=500, detail="Failed to save attack detection or prompts.")
