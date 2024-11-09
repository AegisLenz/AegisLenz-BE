# 사용자와의 프롬프트 세션 관리와 대화 내용을 저장, 조회하는 역할을 함
import os
import json
import datetime
from odmantic import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from datetime import datetime, timedelta, timezone
from models.prompt_model import PromptMessage, PromptSession, Message
from core.redis_driver import RedisDriver
from core.mongodb_driver import mongodb

load_dotenv()

class PromptRepository:
    def __init__(self):
        self.redis_client = RedisDriver()
        self.es_client = AsyncElasticsearch(f"{os.getenv("ES_HOST")}:{os.getenv("ES_PORT")}")
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

    # 새로운 프롬프트 세션을 생성하고 MongoDB에 저장함
    async def create_prompt(self) -> str:
        try:
            prompt_session = PromptSession(
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None),
                updated_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            result = await self.mongodb_engine.save(prompt_session)
            return result.id
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    # MongoDB에서 모든 프롬프트 세션 ID를 가져와 리스트로 반환함
    async def get_all_prompt(self) -> list:
        try:
            prompts = await self.mongodb_engine.find(PromptSession)
            prompt_ids = [str(prompt.id) for prompt in prompts]
            return prompt_ids
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    # 특정 프롬프트 세션의 대화 내용을 조회함
    async def get_prompt_contents(self, prompt_session_id: str) -> list:
        try:
            prompt_session = await self.mongodb_engine.find_one(PromptMessage, PromptMessage.prompt_session_id == ObjectId(prompt_session_id))
            if prompt_session and hasattr(prompt_session, "messages"):
                return prompt_session.messages
            return []
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")


    # 세션 ID가 올바른지 확인하고, 존재하지 않으면 오류를 반환함
    async def validate_prompt_session(self, prompt_session_id: str) -> None:
        if not ObjectId.is_valid(prompt_session_id):
            raise HTTPException(status_code=400, detail="Invalid prompt_session_id format")
 
        prompt_session = await self.mongodb_engine.find_one(PromptSession, PromptSession.id == ObjectId(prompt_session_id))
        if prompt_session is None:
            raise HTTPException(status_code=404, detail="Prompt session not found")


    #  Elasticsearch를 이용해 쿼리를 실행하고 결과를 반환함
    async def find_es_document(self, es_query) -> list:
        try:
            query_result = await self.es_client.search(index=os.getenv("INDEX_NAME"), body=es_query)
            return query_result['hits']['hits']
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


    # MongoDB에서 특정 쿼리 조건에 맞는 데이터를 조회함
    async def find_db_document(self, db_query) -> list:
        try:
            db_query = json.loads(db_query)
            
            # 컬렉션 이름과 find 조건 추출
            collection_name = db_query.get("collection")
            find_filter = db_query.get("find", {})

            # MongoDB 컬렉션 접근 및 조회
            collection = self.mongodb_client[collection_name]
            cursor = collection.find(find_filter)
            result = await cursor.to_list(length=100)  # 결과는 최대 100개까지 가져온다.
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


    # Redis 또는 MongoDB에서 대화기록을 불러와, Redis에서 데이터를 찾지 못할 경우 MongoDB에서 가져옴
    async def load_conversation_history(self, prompt_session_id: str) -> list:
        try:
            # Redis에서 conversation history 조회
            conversation_history = await self.redis_client.get_key(prompt_session_id)
            if conversation_history:
                return json.loads(conversation_history)
            
            # Redis에 없을 경우 MongoDB에서 조회
            object_id = ObjectId(prompt_session_id)
            prompt_message = await self.mongodb_engine.find_one(PromptMessage, PromptMessage.prompt_session_id == object_id)
            if prompt_message:
                # 각 Message 객체를 JSON 형식으로 변환
                formatted_history = [
                    {
                        "timestamp": msg.timestamp.isoformat() if isinstance(msg.timestamp, datetime) else msg["timestamp"],
                        "role": msg.role,
                        "content": msg.content
                    } if isinstance(msg, Message) else msg
                    for msg in prompt_message.messages
                ]
                return formatted_history
            else:
                return []
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    async def save_conversation_history(self, prompt_session_id: str, conversation_history: list) -> None:
        try:            
            # Redis에 저장
            await self.redis_client.set_key(prompt_session_id, json.dumps(conversation_history, ensure_ascii=False))
            
            # MongoDB에 저장
            messages = [msg if isinstance(msg, Message) else Message(**msg) for msg in conversation_history]
            
            object_id = ObjectId(prompt_session_id)
            prompt_message = await self.mongodb_engine.find_one(PromptMessage, PromptMessage.prompt_session_id == object_id)
            if prompt_message:
                prompt_message.messages = messages  # 기존 MongoDB 문서 업데이트
            else:
                prompt_message = PromptMessage(prompt_session_id=prompt_session_id, messages=messages)  # 새로운 대화 세션 생성 및 저장
            
            await self.mongodb_engine.save(prompt_message)

            # PromptSession 업데이트
            prompt_session = await self.mongodb_engine.find_one(PromptSession, PromptSession.id == object_id)
            prompt_session.updated_at = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            
            await self.mongodb_engine.save(prompt_session)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")