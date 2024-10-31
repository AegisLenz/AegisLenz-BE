import os
import json
import datetime
from odmantic import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from models.prompt_model import PromptMessage, PromptSession, Message
from elasticsearch import AsyncElasticsearch
from core.redis_driver import RedisDriver
from core.mongodb_driver import mongodb
from core.logging_config import setup_logger

logger = setup_logger()
load_dotenv()

class PromptRepository:
    def __init__(self):
        self.redis_client = RedisDriver()
        self.es_client = AsyncElasticsearch(f"{os.getenv("ES_HOST")}:{os.getenv("ES_PORT")}")
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

    async def create_prompt(self):
        try:
            prompt_session = PromptSession(
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None),
                updated_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            result = await self.mongodb_engine.save(prompt_session)
            return result.id
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def find_es_document(self, es_query):
        try:
            query_result = await self.es_client.search(index=os.getenv("INDEX_NAME"), body=es_query)
            return json.dumps(query_result['hits']['hits'], ensure_ascii=False)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def find_db_document(self, db_query):
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
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def load_conversation_history(self, prompt_session_id: str):
        try:
            # Redis에서 conversation history 조회
            conversation_history = await self.redis_client.get_key(prompt_session_id)
            if conversation_history:
                return json.loads(conversation_history)
            
            # Redis에 없을 경우 MongoDB에서 조회
            object_id = ObjectId(prompt_session_id)
            prompt_message = await self.mongodb_engine.find_one(PromptMessage, PromptMessage.prompt_session_id == object_id)
            if prompt_message:
                return prompt_message.messages
            else:
                return []
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")

    async def save_conversation_history(self, prompt_session_id: str, conversation_history: list):
        try:
            # Redis에 저장
            await self.redis_client.set_key(prompt_session_id, json.dumps(conversation_history, ensure_ascii=False))
            
            # MongoDB에 저장
            messages = [Message(**msg) for msg in conversation_history]  # 각 메시지를 MongoDB 모델로 변환
            
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

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")