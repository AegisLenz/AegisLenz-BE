import os
import json
import openai
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from datetime import datetime, timedelta, timezone
from repositories.prompt_repository import PromptRepository
from schemas.prompt_schema import PromptChatStreamResponseSchema, CreatePromptResponseSchema
from core.logging_config import setup_logger

logger = setup_logger()

class PromptService:
    def __init__(self, prompt_repository: PromptRepository = Depends()):
        self.prompt_repository = prompt_repository

        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.gpt_client = openai.OpenAI(api_key=self.api_key)

        self.prompt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
        self.prompt_files = {
                "Classify": os.path.join(self.prompt_dir, 'ClassifyPr.txt'),
                "DashBoard": os.path.join(self.prompt_dir, 'DashbPr.txt'),
                "ES": os.path.join(self.prompt_dir, 'onlyES.txt'),
                "DB": os.path.join(self.prompt_dir, 'onlyMDB.txt'),
                "Policy": os.path.join(self.prompt_dir, 'policy.txt'),
                "Summary": os.path.join(self.prompt_dir, 'DetailPr.txt')
            }
        self.init_prompt = {name: [{"role": "system", "content": self.load_prompt(path)}] for name, path in self.prompt_files.items()}

    async def create_prompt(self):
        prompt_id = await self.prompt_repository.create_prompt()
        return prompt_id

    def load_prompt(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    def clean_streaming_chunk(self, chunk):
        choices = getattr(chunk, "choices", None)
        if choices and len(choices) > 0:
            delta = choices[0].delta
            if hasattr(delta, "content") and delta.content:
                return delta.content
        return None

    def clean_response(self, response):
        if response and len(response.choices) > 0:
            if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                return response.choices[0].message.content
        return None

    async def receive_gpt_response(self, target_presona, query):
        conversation = self.init_prompt[target_presona]
        conversation.append(query)

        response = self.gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation,
            response_format={"type": "json_object"}
        )
        return self.clean_response(response)

    def create_stream_response(self, status="processing", type=None, data=None):
        response = PromptChatStreamResponseSchema(status=status, type=type, data=data)
        return json.dumps(response.dict(), ensure_ascii=False) + "\n"

    async def classify_persona(self, query):
        return await self.receive_gpt_response("Classify", query)

    async def dashboard_persona(self, query):
        dashboards = await self.receive_gpt_response("DashBoard", query)
        return json.loads(dashboards).get("selected_dashboards")

    async def es_persona(self, query):
        es_query = await self.receive_gpt_response("ES", query)
        if es_query:
            es_result = await self.prompt_repository.find_es_document(es_query)
            return es_query, es_result
        else:
            raise HTTPException(status_code=400, detail="Failed ElasticSearch query parsing.")

    async def db_persona(self, query):
        db_query = await self.receive_gpt_response("DB", query)
        if db_query:
            db_result = await self.prompt_repository.find_db_document(db_query)
            return db_query, db_result
        else:
            raise HTTPException(status_code=400, detail="Failed MongoDB query parsing.")

    async def policy_persona(self, query):
        return None

    async def process_prompt(self, user_input, prompt_session_id):
        user_input_content = f"사용자의 자연어 질문: {user_input} 답변은 반드시 json 형식으로 나옵니다."
        query = {"role": "user", "content": user_input_content}

        # DB에서 대화 히스토리 가져오기
        conversation_history = await self.prompt_repository.load_conversation_history(prompt_session_id)
        conversation_history.append({"role": "user", "content": user_input, "timestamp": datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()})
        
        # 분류기 데이터
        classify_response = await self.classify_persona(query)
        classify_data = json.loads(classify_response)
        classification_result = classify_data.get("topics")
        logger.info(classification_result)
        
        # 대시보드 데이터
        dashboards = await self.dashboard_persona(query)
        yield self.create_stream_response(type="DashBoard", data=dashboards)
        
        # 분류기 결과에 따른 페르소나 처리
        if classification_result == "DashbPr":
            pass
        elif classification_result in ["onlyES", "onlyMDB", "policy"]:
            if classification_result == "onlyES":
                es_query, es_result = await self.es_persona(query)
                persona_response = json.dumps({
                                                "es_query": es_query,
                                                "es_result": es_result
                                            }, ensure_ascii=False)
                yield self.create_stream_response(type="ESQuery", data=es_query)
                yield self.create_stream_response(type="ESResult", data=es_result)
            elif classification_result == "onlyMDB":
                db_query, db_result = await self.db_persona(query)
                persona_response = json.dumps({
                                                "db_query": db_query,
                                                "db_result": db_result
                                            }, ensure_ascii=False)
                yield self.create_stream_response(type="DBQuery", data=db_query)
                yield self.create_stream_response(type="DBResult", data=db_result)
            elif classification_result == "policy":
                await self.policy_persona(query)
                persona_response = json.dumps()

            logger.info(persona_response)
            # 요약 데이터
            stream = self.gpt_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[query, {"role": "assistant", "content": persona_response}],
                stream=True,
            )

            # 스트리밍 응답 처리
            assistant_response = ""
            for chunk in stream:
                clean_answer = self.clean_streaming_chunk(chunk)
                if clean_answer:
                    assistant_response += clean_answer
                    yield self.create_stream_response(type="Summary", data=clean_answer)

            # 스트리밍이 끝나면 전체 응답을 하나의 문자열로 합쳐 히스토리에 저장
            conversation_history.append({"role": "assistant", "content": assistant_response, "timestamp": datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()})
        else:
            raise HTTPException(status_code=500, detail="Failed Streaming.")
        
        # DB에 대화 히스토리 저장
        await self.prompt_repository.save_conversation_history(prompt_session_id, conversation_history)

        # 스트리밍 완료 메시지 전송
        yield self.create_stream_response(status="complete")

    async def handle_chatgpt_conversation(self, user_input, prompt_id):
        async for chunk in self.process_prompt(user_input, prompt_id):
            yield chunk