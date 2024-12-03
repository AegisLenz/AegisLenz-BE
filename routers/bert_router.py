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
import logging

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Elasticsearch 클라이언트 설정
es_host = os.getenv("ES_HOST", "http://23.23.93.131")
es_port = os.getenv("ES_PORT", "9200")
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
            raise FileNotFoundError(f"{file_path} 경로에 파일이 존재하지 않습니다.")
        
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            logger.info(f"{file_path} 로드 성공")
            return data
    except Exception as e:
        logger.error(f"{file_path} 로드 실패: {e}")
        return {}

# JSON 데이터 로드
TACTICS_TECHNIQUES_MAPPING = load_json(TACTICS_MAPPING_FILE)
elasticsearch_mapping = load_json(ELASTICSEARCH_MAPPING_FILE)

def initialize_elasticsearch_mapping():
    """
    Elasticsearch 매핑(스키마)을 설정하는 함수.
    """
    index_name = "cloudtrail-logs"

    try:
        # 인덱스 존재 여부 확인
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name, body=elasticsearch_mapping)
            logger.info(f"Elasticsearch 인덱스 '{index_name}' 생성 및 매핑 적용 완료.")
        else:
            logger.info(f"Elasticsearch 인덱스 '{index_name}' 이미 존재.")
    except Exception as e:
        logger.error(f"Elasticsearch 매핑 설정 중 오류 발생: {e}")

# Elasticsearch 매핑 초기화
initialize_elasticsearch_mapping()

def normalize_key(key: str) -> str:
    """
    Key를 정규화하여 매핑의 일관성을 유지
    """
    return key.strip().lower().replace(" ", "").replace("-", "")

async def fetch_logs_from_elasticsearch():
    """
    Elasticsearch에서 최근 5개의 로그를 가져오는 함수
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
        logger.info(f"Elasticsearch에서 {len(logs)}개의 로그를 가져왔습니다.")
        return logs
    except es_exceptions.ConnectionError as e:
        logger.error(f"Elasticsearch 연결 오류: {str(e)}")
        return []
    except es_exceptions.RequestError as e:
        logger.error(f"Elasticsearch 요청 오류: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Elasticsearch에서 로그를 가져오는 중 오류 발생: {str(e)}")
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
                            logger.info(f"Type of prediction: {type(prediction)}")

                            normalized_prediction = normalize_key(str(prediction))
                            logger.info(f"Normalized prediction: {normalized_prediction}")

                            tactic = TACTICS_TECHNIQUES_MAPPING.get(normalized_prediction, "Unknown Tactic")
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

                                # Elasticsearch에 저장
                                es.index(index="cloudtrail-logs", body=attack_document)
                                logger.info(f"Elasticsearch에 저장된 문서: {attack_document}")

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
