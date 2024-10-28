import os
import json
import openai
from dotenv import load_dotenv
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from core.redis_driver import RedisDriver
from schemas.prompt_schema import PromptChatStreamResponseSchema


class PromptService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.host_ip = os.getenv("HOST_IP")
        self.elasticsearch_port = os.getenv("ELASTICSEARCH_PORT")
        self.index_name = os.getenv("INDEX_NAME")
        self.prompt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')

        self.gpt_client = openai.OpenAI(api_key=self.api_key)
        self.redis_client = RedisDriver()
        self.es_client = AsyncElasticsearch(f"http://{self.host_ip}:{self.elasticsearch_port}")
        
        self.prompt_files = {
                "Classify": os.path.join(self.prompt_dir, 'ClassifyPr.txt'),
                "DashBoard": os.path.join(self.prompt_dir, 'DashbPr.txt'),
                "ES": os.path.join(self.prompt_dir, 'onlyES.txt'),
                "DB": os.path.join(self.prompt_dir, 'onlyMDB.txt'),
                "Policy": os.path.join(self.prompt_dir, 'policy.txt'),
                "Summary": os.path.join(self.prompt_dir, 'DetailPr.txt')
            }
        self.init_prompt = {name: [{"role": "system", "content": self.load_prompt(path)}] for name, path in self.prompt_files.items()}

    def load_prompt(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    async def load_conversation_history(self, conversation_key):
        conversation_history = await self.redis_client.get_key(conversation_key)
        if conversation_history:
            return json.loads(conversation_history)
        return []

    def clean_streaming_chunk(self, chunk):
        """스트리밍 응답에서 필요 없는 부분을 제거한 후 반환"""
        choices = getattr(chunk, "choices", None)
        if choices and len(choices) > 0:
            delta = choices[0].delta
            if hasattr(delta, "content") and delta.content:
                return delta.content
        return ""

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
        return response

    async def classify_persona(self, query):
        response = await self.receive_gpt_response("Classify", query)
        return self.clean_response(response)

    async def dashboard_persona(self, query):      
        response = await self.receive_gpt_response("DashBoard", query)
        response = self.clean_response(response)
        dashboards = json.loads(response).get("selected_dashboards")
        return dashboards

    async def es_persona(self, query):
        response = await self.receive_gpt_response("ES", query)
        
        es_query = self.clean_response(response)
        if es_query:
            try:
                return es_query
                # query_result = await self.es_client.search(index=self.index_name, query=es_query)
                # query_result = json.dumps(query_result['hits']['hits'], ensure_ascii=False)
                # return query_result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail="Failed ElasticSearch query parsing.")

    async def db_persona(self, query):
        return None

    async def policy_persona(self, query):
        return None

    async def generate_response_by_persona(self, classification, query):
        if classification == "onlyES":
            persona_response = await self.es_persona(query)
        elif classification == "onlyMDB":
            persona_response = await self.db_persona(query)
        elif classification == "policy":
            persona_response = await self.policy_persona(query)
        
        return persona_response

    async def process_prompt(self, user_input, prompt_id):
        user_input_content = f"사용자의 자연어 질문: {user_input} 답변은 반드시 json 형식으로 나옵니다."
        query = {"role": "user", "content": user_input_content}

        conversation_key = f"chat:{prompt_id}"
        conversation_history = await self.load_conversation_history(conversation_key)
        conversation_history.append(query)
        
        if len(conversation_history) > 10:
            conversation_history.pop(1)
        
        assistant_response = ""
        
        classify_response = await self.classify_persona(query)
        classify_data = json.loads(classify_response)
        classification_result = classify_data.get("topics")
        
        dashboards = await self.dashboard_persona(query)
        response = PromptChatStreamResponseSchema(status="processing", type="DashBoard", data=dashboards)
        yield json.dumps(response.dict(), ensure_ascii=False) + "\n"
        
        if classification_result == "DashbPr":
            persona_response = dashboards
        elif classification_result in ["onlyES", "onlyMDB", "Policy"]:
            persona_response = await self.generate_response_by_persona(classification_result, query)
            persona_response = json.dumps(dashboards) + "\n" + persona_response
        else:
            raise HTTPException(status_code=500, detail="Failed classify.")

        # 요약 데이터
        stream = self.gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[query, {"role": "assistant", "content": persona_response}],
            stream=True,
        )

        # 스트리밍 응답 처리
        for chunk in stream:
            clean_answer = self.clean_streaming_chunk(chunk)
            if clean_answer:
                assistant_response += clean_answer
                response = PromptChatStreamResponseSchema(status="processing", type="Summary", data=clean_answer)
                yield json.dumps(response.dict(), ensure_ascii=False) + "\n"
        
        # 스트리밍이 끝나면 전체 응답을 하나의 문자열로 히스토리에 저장
        conversation_history.append({"role": "assistant", "content": assistant_response})
        if len(conversation_history) > 10:
            conversation_history.pop(1)
        await self.redis_client.set_key(conversation_key, json.dumps(conversation_history, ensure_ascii=False))

        # 스트리밍 완료 메시지 전송
        response = PromptChatStreamResponseSchema(status="complete")
        yield json.dumps(response.dict(), ensure_ascii=False) + "\n"

    async def handle_chatgpt_conversation(self, user_input, prompt_id):
        async for chunk in self.process_prompt(user_input, prompt_id):
            yield chunk