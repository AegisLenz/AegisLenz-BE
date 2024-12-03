import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from dotenv import load_dotenv
from database.redis_driver import RedisDriver
from common.logging import setup_logger

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger()

# Elasticsearch 클라이언트 설정
es_host = os.getenv("ES_HOST")
es_port = os.getenv("ES_PORT")
es_index = os.getenv("ES_INDEX", "cloudtrail-logs-*")
es = Elasticsearch(f"{es_host}:{es_port}", max_retries=10, retry_on_timeout=True, request_timeout=120)

# Redis 드라이버 설정
redis_driver = RedisDriver()

# API 라우터 설정
router = APIRouter(prefix="/bert", tags=["bert"])

# JSON 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
COMMON_DIR = os.path.join(PROJECT_ROOT, "common")

TACTICS_MAPPING_FILE = os.path.join(COMMON_DIR, "tactics_mapping.json")
ELASTICSEARCH_MAPPING_FILE = os.path.join(COMMON_DIR, "elasticsearch_mapping.json")

# JSON 데이터 로드 함수
def load_json(file_path):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            logger.info(f"Successfully loaded {file_path}")
            return data
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return {}

# JSON 데이터 로드
tactics_mapping = load_json(TACTICS_MAPPING_FILE)
elasticsearch_mapping = load_json(ELASTICSEARCH_MAPPING_FILE)

def initialize_elasticsearch_mapping():
    """
    Set up Elasticsearch mapping (schema).
    """
    index_name = os.getenv("ES_INDEX", "cloudtrail-logs")

    try:
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name, body=elasticsearch_mapping)
            logger.info(f"Created and applied mapping to Elasticsearch index '{index_name}'.")
        else:
            logger.info(f"Elasticsearch index '{index_name}' already exists.")
    except Exception as e:
        logger.error(f"Error setting up Elasticsearch mapping: {e}")

initialize_elasticsearch_mapping()

def normalize_key(key: str) -> str:
    """
    Normalize a key to maintain consistency in mappings.
    """
    return key.strip().lower().replace(" ", "").replace("-", "")

async def fetch_logs_from_elasticsearch():
    """
    Fetch the last 5 logs from Elasticsearch.
    """
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
        logger.info(f"Fetched {len(logs)} logs from Elasticsearch.")
        return logs
    except es_exceptions.ConnectionError as e:
        logger.error(f"Elasticsearch connection error: {str(e)}")
        return []
    except es_exceptions.RequestError as e:
        logger.error(f"Elasticsearch request error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error fetching logs from Elasticsearch: {str(e)}")
        return []

@router.get("/events", response_model=PredictionSchema)
async def sse_events(bert_service: BERTService = Depends(BERTService)):
    async def event_generator():
        while True:
            try:
                logs = await fetch_logs_from_elasticsearch()
                if logs:
                    for log in logs:
                        source_ip = log.get("sourceIPAddress")
                        if source_ip:
                            try:
                                await redis_driver.set_log_queue(source_ip, log)
                                logger.info(f"Log for {source_ip} added to Redis.")
                            except Exception as redis_error:
                                logger.error(f"Error adding log to Redis: {str(redis_error)}")
                                continue

                for source_ip in {log.get("sourceIPAddress") for log in logs if log.get("sourceIPAddress")}:
                    try:
                        buffer = await redis_driver.get_log_queue(source_ip)
                        if len(buffer) == 5:
                            prediction = await bert_service.predict_attack(buffer)
                            
                            logger.info(f"Raw prediction value for {source_ip}: {prediction}")
                            normalized_prediction = normalize_key(str(prediction))
                            logger.info(f"Normalized prediction: {normalized_prediction}")

                            tactic = tactics_mapping.get(normalized_prediction, "Unknown Tactic")
                            logger.info(f"Mapped tactic: {tactic}")

                            if tactic == "Unknown Tactic":
                                logger.warning(f"Mapping failed for prediction: {prediction} (normalized: {normalized_prediction})")

                            if prediction != 'No Attack':
                                attack_document = {
                                    **log,
                                    "mitreAttackTactic": tactic,
                                    "mitreAttackTechnique": str(prediction),
                                    "attack_time": datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()
                                }

                                # BERT 결과 Elasticsearch에 저장
                                es.index(index="cloudtrail-logs", body=attack_document)
                                logger.info(f"Document saved to Elasticsearch: {attack_document}")

                                user_id = log.get("userIdentity", {}).get("arn", "unknown_user")
                                attack_info = {
                                    "attack_time": attack_document["attack_time"],
                                    "attack_type": [tactic],
                                    "logs": json.dumps(attack_document)
                                }
                                try:
                                    prompt_session_id = await bert_service.process_after_detection(user_id, attack_info)
                                    logger.info(f"Session ID {prompt_session_id} generated for user {user_id}.")
                                except Exception as e:
                                    logger.error(f"Error in process_after_detection for {user_id}: {e}")
                                yield f"data: {json.dumps(attack_document, ensure_ascii=False)}\n\n"

                            await redis_driver.log_prediction(source_ip, {"prediction": str(prediction)})
                    except Exception as e:
                        logger.error(f"Error processing prediction for {source_ip}: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Error in event generator: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            
            await asyncio.sleep(5)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
