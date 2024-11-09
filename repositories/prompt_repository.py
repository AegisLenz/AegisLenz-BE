import os
import json
from odmantic import ObjectId
from pymongo import ASCENDING
from dotenv import load_dotenv
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from datetime import datetime, timedelta, timezone
from models.prompt_model import PromptMessage, PromptSession, Message, PromptChat
from core.redis_driver import RedisDriver
from core.mongodb_driver import mongodb

load_dotenv()


class PromptRepository:
    def __init__(self):
        self.redis_client = RedisDriver()
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
                PromptChat.prompt_session_id == ObjectId(prompt_session_id)
            ).sort("created_at", ASCENDING)
            if prompt_chats:
                return prompt_chats
            else:
                return []
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

    async def save_chat(self, prompt_session_id: str, role: str, content: str, recommend_questions: list) -> None:
        try:
            prompt_session_id = ObjectId(prompt_session_id)
            prompt_chat = PromptChat(
                prompt_session_id=prompt_session_id,
                role=role,
                content=content,
                recommend_questions=recommend_questions,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )

            # redis에 저장
            await self.redis_client.set_key(prompt_session_id, prompt_chat.json())

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