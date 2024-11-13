import os
import json
from typing import Optional, List, Dict
from odmantic import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from datetime import datetime, timedelta, timezone
from models.prompt_model import PromptSession, PromptChat
from core.redis_driver import RedisDriver
from core.mongodb_driver import mongodb
from utils.prompt.convert_dates_in_query import convert_dates_in_query


class PromptRepository:
    def __init__(self):
        self.redis_client = RedisDriver()
        load_dotenv()
        self.es_client = AsyncElasticsearch(f"{os.getenv("ES_HOST")}:{os.getenv("ES_PORT")}")
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

    async def create_prompt(self, attack_detection_id: Optional[str] = None, recommend_history: Optional[List[Dict]] = None, recommend_questions: Optional[List[str]] = None) -> str:
        try:
            attack_detection_id = ObjectId(attack_detection_id) if attack_detection_id else None
            recommend_history = recommend_history or []
            recommend_questions = recommend_questions or []

            prompt_session = PromptSession(
                attack_detection_id=attack_detection_id,
                recommend_history=recommend_history,
                recommend_questions=recommend_questions,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None),
                updated_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            result = await self.mongodb_engine.save(prompt_session)
            return result.id
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def find_prompt_session(self, prompt_session_id: str) -> PromptSession:
        try:
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.id == ObjectId(prompt_session_id)
            )
            return prompt_session
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
        try:
            if not ObjectId.is_valid(prompt_session_id):
                raise HTTPException(status_code=400, detail="Invalid prompt_session_id format")
    
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.id == ObjectId(prompt_session_id)
            )
            if prompt_session is None:
                raise HTTPException(status_code=404, detail="Prompt session not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    async def check_attack_detection_id_exist(self, prompt_session_id: str) -> bool:
        try:
            result = await self.mongodb_engine.find_one(
                PromptSession,
                {
                    "_id": ObjectId(prompt_session_id),
                    "attack_detection_id": {"$exists": True, "$ne": None}
                }
            )
            return result is not None
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

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
            db_query = convert_dates_in_query(db_query)
            results = await self.mongodb_client.user_assets.find(db_query).to_list(length=100)  # 최대 100개 문서 가져오기
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    
    async def save_chat(self, prompt_session_id: str, role: str, content: str) -> None:
        try:
            prompt_session_id = ObjectId(prompt_session_id)
            prompt_chat = PromptChat(
                prompt_session_id=prompt_session_id,
                role=role,
                content=content,
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

    async def find_recommend_data(self, prompt_session_id: str) -> tuple[list, list]:
        try:
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.id == ObjectId(prompt_session_id)
            )
            if prompt_session:
                return prompt_session.recommend_history, prompt_session.recommend_questions
            else:
                return [], []
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    async def update_recommend_data(self, prompt_session_id: str, recomm_history: list, recomm_questions: list):
        try:
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.id == ObjectId(prompt_session_id)
            )
            prompt_session.recommend_history = recomm_history
            prompt_session.recommend_questions = recomm_questions
            await self.mongodb_engine.save(prompt_session)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while updating recommend data: {str(e)}")