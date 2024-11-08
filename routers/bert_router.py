import os
import json
import asyncio
import logging
from collections import deque
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from elasticsearch import Elasticsearch
from core.redis_driver import RedisDriver
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Elasticsearch 클라이언트 설정
es_host = os.getenv("ES_HOST", "http://23.23.93.131")
es_port = os.getenv("ES_PORT", "9200")
es_index = os.getenv("ES_INDEX", "cloudtrail-logs-*")
es = Elasticsearch(f"{es_host}:{es_port}", max_retries=10, retry_on_timeout=True, request_timeout=120)

# Redis 드라이버 설정
redis_driver = RedisDriver()

# API 라우터 설정
router = APIRouter(prefix="", tags=["BERT"])

# 로그 버퍼 설정 (최대 크기 5)
log_buffer = deque(maxlen=5)

# Redis 연결 테스트 엔드포인트
@router.get("/bert/test-redis-connection")
async def test_redis_connection():
    """
    Redis 연결 테스트 엔드포인트.
    """
    try:
        logger.info("Attempting to connect to Redis...")
        await redis_driver.redis_client.ping()
        logger.info("Redis 연결 성공")
        return {"status": "Redis 연결 성공"}
    except Exception as e:
        logger.error(f"Redis 연결 실패: {str(e)}")
        return {"status": "Redis 연결 실패", "error": str(e)}

# 테스트 엔드포인트: Elasticsearch 로그 가져오기
@router.get("/bert/test-fetch-logs")
async def test_fetch_logs():
    logs = await fetch_logs_from_elasticsearch()
    return logs

# 테스트 엔드포인트: Redis 로그 추가 테스트
@router.get("/bert/test-add-log")
async def test_add_log():
    test_ip = "1.233.83.207"
    test_log = {"event": "Test log"}
    await redis_driver.add_log_to_cluster(test_ip, test_log)
    return {"status": "log added"}

# Elasticsearch에서 로그 데이터를 가져오는 함수
async def fetch_logs_from_elasticsearch():
    try:
        response = es.search(
            index=es_index,
            body={
                "size": 5,
                "sort": [{"@timestamp": {"order": "desc"}}],
                "query": {"match_all": {}}
            }
        )
        logs = [hit["_source"] for hit in response["hits"]["hits"]]
        return logs
    except Exception as e:
        print(f"Error fetching logs from Elasticsearch: {str(e)}")
        return []