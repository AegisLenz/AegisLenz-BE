import os
import json
import openai
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from repositories.prompt_repository import PromptRepository
from schemas.prompt_schema import PromptChatStreamResponseSchema
from core.logging_config import setup_logger

logger = setup_logger()


class PromptService:
    def __init__(self, prompt_repository: PromptRepository = Depends()):
        self.prompt_repository = prompt_repository
        load_dotenv()
        self.gpt_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.init_prompt = self._load_all_prompts()

    def _load_all_prompts(self):
        prompt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
        prompt_files = {
            "Classify": "ClassifyPr.txt",
            "ES": "onlyES.txt",
            "DB": "onlyMDB.txt",
            "Policy": "policy.txt",
            "Summary": "DetailPr.txt"
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
    
    async def create_prompt(self):
        return await self.prompt_repository.create_prompt()

    async def get_all_prompt(self):
        return await self.prompt_repository.get_all_prompt()

    async def get_prompt_chats(self, prompt_session_id: str):
        await self.prompt_repository.validate_prompt_session(prompt_session_id)
        return await self.prompt_repository.get_prompt_chats(prompt_session_id)

    def _clean_streaming_chunk(self, chunk):
        choices = getattr(chunk, "choices", None)
        return choices[0].delta.content if choices and choices[0].delta.content else None

    def _clean_response(self, response):
        choices = getattr(response, "choices", [])
        return choices[0].message.content if choices and hasattr(choices[0].message, 'content') else None

    async def _receive_gpt_response(self, messages, json_format=True):
        try:
            response_format = {"type": "json_object"} if json_format else None
            response = self.gpt_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format=response_format
            )
            return self._clean_response(response)
        except Exception as e:
            logger.error(f"Error fetching GPT response: {e}")
            raise HTTPException(status_code=500, detail="GPT API error")

    async def _classify_persona(self, query):
        messages = self.init_prompt["Classify"]
        messages.append(query)
        response = await self._receive_gpt_response(messages)
        responss_data = json.loads(response)
        persona_type = responss_data.get("topics")
        return persona_type

    async def _es_persona(self, query):
        messages = self.init_prompt["ES"]
        messages.append(query)
        es_query = await self._receive_gpt_response(messages)
        if es_query:
            es_result = await self.prompt_repository.find_es_document(es_query)
            return es_query, es_result
        else:
            raise HTTPException(status_code=400, detail="Failed ElasticSearch query parsing.")

    async def _db_persona(self, query):
        messages = self.init_prompt["DB"]
        messages.append(query)
        db_query = await self._receive_gpt_response(messages)
        if db_query:
            db_result = await self.prompt_repository.find_db_document(db_query)
            return db_query, db_result
        else:
            raise HTTPException(status_code=400, detail="Failed MongoDB query parsing.")

    async def _policy_persona(self, query):
        return None

    def _create_stream_response(self, status="processing", type=None, data=None):
        response = PromptChatStreamResponseSchema(status=status, type=type, data=data)
        return json.dumps(response.dict(), ensure_ascii=False) + "\n"

    async def _stream_gpt_summary(self, messages):
        stream = self.gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            clean_answer = self._clean_streaming_chunk(chunk)
            if clean_answer:
                yield self._create_stream_response(type="Summary", data=clean_answer), clean_answer
    
    async def handle_normal_prompt(self, user_question, prompt_session_id):
        user_content = f"사용자의 자연어 질문: {user_question} 답변은 반드시 json 형식으로 나옵니다."
        query = {"role": "user", "content": user_content}

        # 분류기 결과
        persona_type = await self._classify_persona(query)
        
        # 분류기 결과에 따른 페르소나 처리
        if persona_type in ["ES", "DB"]:
            if persona_type == "ES":
                es_query, es_result = await self._es_persona(query)
                persona_response = json.dumps({
                                                "es_query": es_query,
                                                "es_result": es_result
                                            }, ensure_ascii=False)
                yield self._create_stream_response(type="ESQuery", data=es_query)
                yield self._create_stream_response(type="ESResult", data=es_result)
            elif persona_type == "DB":
                db_query, db_result = await self._db_persona(query)
                persona_response = json.dumps({
                                                "db_query": db_query,
                                                "db_result": db_result
                                            }, ensure_ascii=False)
                yield self._create_stream_response(type="DBQuery", data=db_query)
                yield self._create_stream_response(type="DBResult", data=db_result)

            # 요약 데이터
            summary_conversation = self.init_prompt["Summary"]
            summary_conversation.append({
                "role": "user",
                "content": f"{user_content}\n{persona_type} 응답: {persona_response}"
            })
            
            assistant_response = ""
            async for chunk, assistant_text in self._stream_gpt_summary(summary_conversation):
                assistant_response += assistant_text  # assistant_response에 응답을 누적 저장
                yield chunk
        
        elif persona_type == "Normal":
            assistant_response = ""
            async for chunk, assistant_text in self._stream_gpt_summary([{"role": "user", "content": user_question}]):
                assistant_response += assistant_text  # assistant_response에 응답을 누적 저장
                yield chunk
        else:
            raise HTTPException(status_code=500, detail="Failed Classify.")
         
        # 스트리밍 완료 메시지 전송
        yield self._create_stream_response(status="complete")

        # DB에 채팅 내역 저장
        await self.prompt_repository.save_chat(prompt_session_id, "user", user_question)
        await self.prompt_repository.save_chat(prompt_session_id, "assistant", assistant_response)
    
    async def handle_chat(self, user_question: str, prompt_session_id: str):
        try:
            # PromptSession 아이디 유효성 확인
            await self.prompt_repository.validate_prompt_session(prompt_session_id)

            # 프롬프트 처리 및 응답 스트리밍
            is_attack_prompt = await self.prompt_repository.check_attack_detection_id_exist(prompt_session_id)
            if is_attack_prompt:
                async for chunk in self.handle_attack_prompt(user_question, prompt_session_id):
                    yield chunk
            else:
                async for chunk in self.handle_normal_prompt(user_question, prompt_session_id):
                    yield chunk

        except HTTPException as e:
            yield json.dumps({"error": e.detail, "status_code": e.status_code})
        except Exception as e:
            yield json.dumps({"error": str(e), "status_code": 500})