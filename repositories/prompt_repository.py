import os
import json
from typing import Optional
from odmantic import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from datetime import datetime, timedelta, timezone
from models.prompt_model import PromptSession, PromptChat
from core.redis_driver import RedisDriver
from core.mongodb_driver import mongodb


class PromptRepository:
    def __init__(self):
        self.redis_client = RedisDriver()
        load_dotenv()
        self.es_client = AsyncElasticsearch(f"{os.getenv("ES_HOST")}:{os.getenv("ES_PORT")}")
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

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

    async def get_all_prompt(self) -> list:
        try:
            prompts = await self.mongodb_engine.find(PromptSession)
            prompt_ids = [str(prompt.id) for prompt in prompts]
            return prompt_ids
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    async def get_prompt_chats(self, prompt_session_id: str) -> list:
        try:
            prompt_chats = await self.mongodb_engine.find(
                PromptChat,
                PromptChat.prompt_session_id == ObjectId(prompt_session_id),
                sort=PromptChat.created_at
            )
            return prompt_chats if prompt_chats else []

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    async def validate_prompt_session(self, prompt_session_id: str) -> None:
        if not ObjectId.is_valid(prompt_session_id):
            raise HTTPException(status_code=400, detail="Invalid prompt_session_id format")
 
        prompt_session = await self.mongodb_engine.find_one(
            PromptSession,
            PromptSession.id == ObjectId(prompt_session_id)
        )
        if prompt_session is None:
            raise HTTPException(status_code=404, detail="Prompt session not found")

    async def find_es_document(self, es_query) -> list:
        try:
            query_result = await self.es_client.search(
                index=os.getenv("INDEX_NAME"),
                body=es_query
            )
            return query_result['hits']['hits']
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

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

    async def save_chat(self, prompt_session_id: str, role: str, content: str, recommend_questions: Optional[list] = None) -> None:
        try:
            prompt_session_id = ObjectId(prompt_session_id)
            prompt_chat = PromptChat(
                prompt_session_id=prompt_session_id,
                role=role,
                content=content,
                recommend_questions=recommend_questions or [],
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )

            # redis에 저장
            await self.redis_client.set_key(str(prompt_session_id), prompt_chat.json())

            # mongoDB에 저장
            await self.mongodb_engine.save(prompt_chat)

            # PromptSession 마지막 업데이트 시간 업데이트
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.id == prompt_session_id
            )
            prompt_session.updated_at = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            await self.mongodb_engine.save(prompt_session)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")