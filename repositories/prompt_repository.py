import os
import json
from typing import Optional, List, Dict
from odmantic import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from datetime import datetime, timedelta, timezone
from models.prompt_model import PromptSession, PromptChat
from database.redis_driver import RedisDriver
from database.mongodb_driver import mongodb
from services.prompt.query_parser import convert_dates_in_query, parse_db_response, parse_es_response
from common.logging import setup_logger

logger = setup_logger()
load_dotenv()


class PromptRepository:
    def __init__(self):
        self.redis_client = RedisDriver()
        self.es_client = AsyncElasticsearch(f"{os.getenv("ES_HOST")}:{os.getenv("ES_PORT")}")
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

    async def create_prompt(self, user_id: str, attack_detection_id: Optional[ObjectId] = None,
                            recommend_history: Optional[List[Dict]] = None,
                            recommend_questions: Optional[List[str]] = None,
                            title: Optional[str] = None) -> str:
        try:
            prompt_session = PromptSession(
                title=title,
                attack_detection_id=ObjectId(attack_detection_id) if attack_detection_id else None,
                recommend_history=recommend_history or [],
                recommend_questions=recommend_questions or [],
                user_id=user_id,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None),
                updated_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            result = await self.mongodb_engine.save(prompt_session)
            logger.info(f"Prompt session created successfully for user_id: {user_id}, session_id: {result.id}")
            return result.id
        except Exception as e:
            logger.error(
                f"Error creating prompt session. User ID: '{user_id}', Title: '{title}', "
                f"Attack Detection ID: '{attack_detection_id}', Error: {str(e)}"
            )
            raise HTTPException(status_code=500, detail=f"Failed to create a prompt session: {str(e)}")

    async def find_prompt_session(self, prompt_session_id: str) -> PromptSession:
        try:
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.id == ObjectId(prompt_session_id)
            )
            return prompt_session
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def get_all_prompt(self, user_id: str) -> list:
        try:
            prompts = await self.mongodb_engine.find(
                PromptSession,
                PromptSession.user_id == user_id,
                sort=(PromptSession.updated_at, PromptSession.updated_at.desc())
            )
            return prompts
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

    async def find_es_document(self, es_query: str) -> list:
        try:
            logger.info("Received ES query: %s", es_query)
            
            query_result = await self.es_client.search(
                index=os.getenv("ES_INDEX"),
                body=es_query
            )
            logger.info("Raw query result: %s", query_result)

            result = parse_es_response(query_result)
            logger.info("Final extracted result: %s", result)

            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def find_db_document(self, db_query: str) -> list:
        try:
            logger.info("Received DB query: %s", db_query)
            
            parsed_query = json.loads(db_query)
            processed_query = convert_dates_in_query(parsed_query)
            logger.info("Processed query after date conversion: %s", processed_query)

            query_result = await self.mongodb_client.command(processed_query)
            logger.info("Raw query result: %s", query_result)

            first_batch = query_result.get("cursor", {}).get("firstBatch", [])
            logger.info(type(first_batch))
            result = parse_db_response(first_batch)
            logger.info(type(result))
            logger.info("Final extracted result: %s", result)

            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    
    async def save_chat(self, prompt_session_id: str, role: str, content: str, query: Optional[str] = None) -> None:
        try:
            prompt_session_id = ObjectId(prompt_session_id)
            prompt_chat = PromptChat(
                prompt_session_id=prompt_session_id,
                role=role,
                content=content,
                query=query,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
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

    async def save_title(self, prompt_session_id: str, title: str):
        try:
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.id == ObjectId(prompt_session_id)
            )
            prompt_session.title = title
            await self.mongodb_engine.save(prompt_session)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while save title: {str(e)}")

    async def find_prompt_session_by_attack_detection_id(self, attack_detection_id: ObjectId):
        try:
            prompt_session = await self.mongodb_engine.find_one(
                PromptSession,
                PromptSession.attack_detection_id == ObjectId(attack_detection_id)
            )
            return prompt_session
        except Exception as e:
            logger.error(f"Error fetching prompt session for attack_detection_id={attack_detection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch prompt session: {str(e)}")
