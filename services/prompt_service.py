import json
from bson import json_util
from fastapi import HTTPException, Depends
from datetime import datetime
from typing import Any
from services.gpt_service import GPTService
from services.asset_service import AssetService
from repositories.prompt_repository import PromptRepository
from repositories.bert_repository import BertRepository
from repositories.asset_repository import AssetRepository
from repositories.report_repository import ReportRepository
from schemas.prompt_schema import PromptChatStreamResponseSchema, GetPromptContentsSchema, GetPromptContentsResponseSchema, GetAllPromptResponseSchema, PromptSessionSchema
from services.policy.filter_original_policy import filter_original_policy
from common.logging import setup_logger

logger = setup_logger()


class PromptService:
    def __init__(self, prompt_repository: PromptRepository = Depends(), bert_repository: BertRepository = Depends(),
                 asset_repository: AssetRepository = Depends(), report_repository: ReportRepository = Depends(),
                 asset_service: AssetService = Depends(), gpt_service: GPTService = Depends()):
        self.prompt_repository = prompt_repository
        self.bert_repository = bert_repository
        self.asset_repository = asset_repository
        self.report_repository = report_repository
        self.asset_service = asset_service
        self.gpt_service = gpt_service
        try:
            self.init_prompts = self.gpt_service._load_prompts()
            logger.debug("Successfully loaded initial prompts.")
        except Exception as e:
            logger.error(f"Failed to load initial prompts: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize prompts.")
    
    async def create_prompt(self, user_id: str) -> str:
        return await self.prompt_repository.create_prompt(user_id)

    async def get_all_prompt(self, user_id: str) -> GetAllPromptResponseSchema:
        find_prompts = await self.prompt_repository.get_all_prompt(user_id)
        if not find_prompts:
            logger.warning(f"No prompts found for user_id={user_id}")
            return GetAllPromptResponseSchema(prompts=[])

        prompts = [
            PromptSessionSchema(prompt_id=prompt.id, prompt_title=prompt.title, prompt_updated_at=prompt.updated_at)
            for prompt in find_prompts]
        return GetAllPromptResponseSchema(prompts=prompts)

    async def get_prompt_chats(self, prompt_session_id: str) -> GetPromptContentsResponseSchema:
        await self.prompt_repository.validate_prompt_session(prompt_session_id)

        prompt_session = await self.prompt_repository.find_prompt_session(prompt_session_id)
        title = prompt_session.title

        prompt_chats = await self.prompt_repository.get_prompt_chats(prompt_session_id)
        chats = [
            GetPromptContentsSchema(role=chat.role, content=chat.content)
            for chat in prompt_chats
        ]
        
        # 공격에 대한 프롬프트 대화창인 경우 관련 정보 가져오기
        report, recommend_questions, least_privilege_policy, attack_graph = None, None, None, None

        is_attack_prompt = await self.prompt_repository.check_attack_detection_id_exist(prompt_session_id)
        if is_attack_prompt:
            recommend_questions = prompt_session.recommend_questions[:3]

            find_attack_detection = await self.bert_repository.find_attack_detection(prompt_session.attack_detection_id)
            if find_attack_detection:
                least_privilege_policy = find_attack_detection.least_privilege_policy
                attack_graph = find_attack_detection.attack_graph
            else:
                raise HTTPException(status_code=404, detail=f"attack_detection not found with ID: {prompt_session.attack_detection_id}")
        
            find_report = await self.report_repository.find_report_by_attack_detection(prompt_session.attack_detection_id)
            if find_report:
                report = find_report.report_content
            else:
                raise HTTPException(status_code=404, detail=f"report not found with ID: {prompt_session.attack_detection_id}")

        return GetPromptContentsResponseSchema(
            title=title,
            chats=chats,
            report=report,
            attack_graph=attack_graph,
            least_privilege_policy=least_privilege_policy,
            init_recommend_questions=recommend_questions
        )

    async def _load_chat_history(self, prompt_session_id: str) -> list:
        find_history = await self.prompt_repository.get_prompt_chats(prompt_session_id)
        find_history = find_history[-8:]
        return [{"role": h.role, "content": f"{h.content} 생성된 쿼리: {h.query}" if h.query else h.content}
                for h in find_history]

    async def _classify_persona(self, user_query, history: list) -> str:
        classify_prompt = history
        classify_prompt.append(self.init_prompts["Classify"][0])
        classify_prompt.append(user_query)

        response = await self.gpt_service.get_response(classify_prompt)
        responss_data = json.loads(response)
        persona_type = responss_data.get("topics")
        return persona_type

    async def _es_persona(self, user_query, history: list) -> dict[str, Any]:
        es_prompt = history
        es_prompt.append(self.init_prompts["ES"][0])
        es_prompt.append(user_query)

        es_query = await self.gpt_service.get_response(es_prompt)
        if es_query:
            es_result = await self.prompt_repository.find_es_document(es_query)
            return es_query, es_result
        else:
            raise HTTPException(status_code=500, detail="Unable to generate a valid Elasticsearch query.")

    async def _db_persona(self, user_query, history: list, user_id: str) -> dict[str, Any]:
        await self.asset_service.update_asset(user_id)  # 자산 업데이트

        db_prompt = history
        db_prompt.append(self.init_prompts["DB"][0])
        db_prompt.append(user_query)

        db_query = await self.gpt_service.get_response(db_prompt)
        if db_query:
            db_result = await self.prompt_repository.find_db_document(db_query)
            return db_query, db_result
        else:
            raise HTTPException(status_code=500, detail="Unable to generate a valid MongoDB query.")

    async def _recommend_questions_persona(self, recomm_history, pre_recomm_questions) -> list:
        response = await self.gpt_service.get_response(recomm_history, json_format=False, recomm=True)
        new_questions = response.splitlines()
        unique_questions = [
            question.strip().replace('\"', '') for question in new_questions
            if question.strip() and question.strip().replace('\"', '') not in pre_recomm_questions
        ]
        return unique_questions[:3]

    async def _create_recommend_questions(self, prompt_session_id: str, user_question: str, assistant_response: str) -> list:
        recomm_history, pre_recomm_questions = await self.prompt_repository.find_recommend_data(prompt_session_id)
        
        prompt_text = f"{user_question}\n 이전과 중복되지 않는 세 줄 질문을 생성해 주세요. 출력은 반드시 세개의 간단한 질문으로만 주세요."
        recomm_history.append({"role": "user", "content": prompt_text})
        recomm_history.append({"role": "assistant", "content": assistant_response})

        recomm_questions = await self._recommend_questions_persona(recomm_history, pre_recomm_questions)
        if recomm_questions:
            recomm_history.append({"role": "assistant", "content": "\n".join(recomm_questions)})
            pre_recomm_questions.extend(recomm_questions)

        await self.prompt_repository.update_recommend_data(prompt_session_id, recomm_history, pre_recomm_questions)
        return recomm_questions

    async def _create_prompt_title(self, prompt_session_id: str, user_question: str):
        prompt_session = await self.prompt_repository.find_prompt_session(prompt_session_id)
        if not prompt_session.title:
            title_prompt = [{"role": "system", "content": "다음 사용자의 요청을 요약하여 15자 이내로 제목을 생성해 주세요.\n"}]
            title_prompt.append({"role": "user", "content": user_question})
            title = await self.gpt_service.get_response(title_prompt, json_format=False)
            await self.prompt_repository.save_title(prompt_session_id, title)
        else:
            pass

    def _create_stream_response(self, status="processing", type=None, data=None) -> str:
        try:
            if data is not None:
                if isinstance(data, dict):
                    data = json.dumps(data, ensure_ascii=False).replace('\"', '')
                elif isinstance(data, str):
                    data = data.replace('\"', '')
                elif isinstance(data, list):
                    pass

            response = PromptChatStreamResponseSchema(status=status, type=type, data=data)
            return json.dumps(response.dict(), ensure_ascii=False) + "\n"
        except Exception as e:
            logger.error(f"Error creating stream response: {e}")
            raise HTTPException(status_code=500, detail="Failed to create stream response.")

    async def process_prompt(self, user_question: str, prompt_session_id: str, user_id: str, is_attack=False):
        try:
            user_content = (
                "현재 날짜와 시간은 {time}입니다. "
                "이 시간에 맞춰서 작업을 진행해주세요. 사용자의 자연어 질문: {question} "
                "답변은 반드시 json 형식으로 나옵니다. "
                "만약 해당 질문에서 이전 내용을 반영해야 한다면, 이전 내용의 user와 assistant를 참고하여 응답을 반환하세요."
            ).format(
                time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                question=user_question
            )
            user_query = {"role": "user", "content": user_content}
            query = None
            history = await self._load_chat_history(prompt_session_id)  # 이전 대화 내역 가져오기

            # 분류기 페르소나 로직 수행
            try:
                persona_type = await self._classify_persona(user_query, history)
                logger.info(f"Persona type classified: {persona_type}")
            except Exception as e:
                logger.error(f"Error during persona classification: {e}")
                raise HTTPException(status_code=500, detail="Persona classification failed.")

            # 분류기 결과에 따른 페르소나 로직 수행
            if persona_type in ["ES", "DB"]:
                if persona_type == "ES":
                    query, query_result = await self._es_persona(user_query, history)
                    yield self._create_stream_response(type="ESQuery", data=query)
                    yield self._create_stream_response(type="ESResult", data=query_result)
                    persona_response = json.dumps({"es_query": query, "es_result": query_result}, ensure_ascii=False)
                elif persona_type == "DB":
                    query, query_result = await self._db_persona(user_query, history, user_id)
                    yield self._create_stream_response(type="DBQuery", data=query)
                    yield self._create_stream_response(type="DBResult", data=json.dumps(query_result, default=json_util.default, ensure_ascii=False))
                    persona_response = json.dumps({"db_query": query, "db_result": query_result}, default=json_util.default, ensure_ascii=False)

                summary_prompt = self.init_prompts["Summary"]
                summary_prompt.append({
                    "role": "user",
                    "content": f"{user_content}\n{persona_type} 응답: {persona_response}"
                })

                # 응답 페르소나
                assistant_response = ""
                async for chunk in self.gpt_service.stream_response(summary_prompt):
                    assistant_response += chunk
                    yield self._create_stream_response(type="Summary", data=chunk)
            elif persona_type == "Policy":
                prompt_session = await self.prompt_repository.find_prompt_session(prompt_session_id)
                if not prompt_session:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Prompt session with ID: {prompt_session_id} does not exist or could not be retrieved."
                    )

                attack_detection = await self.bert_repository.find_attack_detection(prompt_session.attack_detection_id)
                if not attack_detection:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Attack detection data missing or incomplete for ID: {prompt_session.attack_detection_id}"
                    )

                least_privilege_policy_data = attack_detection.least_privilege_policy
                if not least_privilege_policy_data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Least privilege policy not found in attack detection with ID: {prompt_session.attack_detection_id}"
                    )

                least_privilege_policy = least_privilege_policy_data.get("least_privilege_policy")
                original_policy = least_privilege_policy_data.get("original_policy")

                policy_content = self.init_prompts["Policy"][0]["content"].format(
                    original_policy=json.dumps(filter_original_policy(original_policy, least_privilege_policy), indent=2),
                    least_privilege_policy=json.dumps(least_privilege_policy, indent=2),
                )

                summary_prompt = history
                summary_prompt.append({"role": "system", "content": policy_content})
                summary_prompt.append({"role": "user", "content": user_question})

                # 응답 페르소나
                assistant_response = ""
                async for chunk in self.gpt_service.stream_response(summary_prompt):
                    assistant_response += chunk
                    yield self._create_stream_response(type="Summary", data=chunk)
            elif persona_type == "Normal":
                summary_prompt = history
                summary_prompt.append({"role": "user", "content": user_question})

                # 응답 페르소나
                assistant_response = ""
                async for chunk in self.gpt_service.stream_response(summary_prompt):
                    assistant_response += chunk
                    yield self._create_stream_response(type="Summary", data=chunk)
            else:
                raise HTTPException(status_code=500, detail="Unknown persona type.")

            # 공격에 대한 프롬프트 대화창인 경우 추천 질문 생성
            if is_attack:
                recomm_questions = await self._create_recommend_questions(prompt_session_id, user_question, assistant_response)
                yield self._create_stream_response(type="RecommendQuestions", data=recomm_questions)

            yield self._create_stream_response(status="complete")  # 스트리밍 완료 메시지 전송
            await self._create_prompt_title(prompt_session_id, user_question)  # 프롬프트 타이틀 생성

            await self.prompt_repository.save_chat(prompt_session_id, "user", user_question)
            await self.prompt_repository.save_chat(prompt_session_id, "assistant", assistant_response, query)
        except Exception as e: 
            logger.error(f"Error processing prompt for session_id: {prompt_session_id}, user_id: {user_id}, error: {str(e)}") 
            raise HTTPException(status_code=500, detail=f"Failed to process prompt.")

    async def handle_chat(self, user_question: str, prompt_session_id: str, user_id: str):
        try:
            # PromptSession 아이디 유효성 확인
            await self.prompt_repository.validate_prompt_session(prompt_session_id)

            # 프롬프트 처리 및 응답 스트리밍
            is_attack_prompt = await self.prompt_repository.check_attack_detection_id_exist(prompt_session_id)
            if is_attack_prompt:
                async for chunk in self.process_prompt(user_question, prompt_session_id, user_id, is_attack=True):
                    yield chunk
            else:
                async for chunk in self.process_prompt(user_question, prompt_session_id, user_id, is_attack=False):
                    yield chunk
        except Exception as e:
            logger.error(f"Unexpected error during handling the chat: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred while handling the chat.")
