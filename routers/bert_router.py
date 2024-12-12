import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from dotenv import load_dotenv
from database.redis_driver import RedisDriver
from services.es_service import ElasticsearchService, ElasticsearchServiceError
from common.logging import setup_logger

load_dotenv()
logger = setup_logger()

redis_driver = RedisDriver()
es_service = ElasticsearchService()

router = APIRouter(prefix="/bert", tags=["bert"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
COMMON_DIR = os.path.join(PROJECT_ROOT, "common")

TACTICS_MAPPING_FILE = os.path.join(COMMON_DIR, "tactics_mapping.json")
ELASTICSEARCH_MAPPING_FILE = os.path.join(COMMON_DIR, "elasticsearch_mapping.json")

LOGS_INDEX_NAME = os.getenv("ES_INDEX")
ATTACK_INDEX_NAME = os.getenv("ES_ATTACK_INDEX")

BUFFER_SIZE = 5

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

tactics_mapping = load_json(TACTICS_MAPPING_FILE)
elasticsearch_mapping = load_json(ELASTICSEARCH_MAPPING_FILE)

def normalize_key(key: str) -> str:
    """키를 정규화하여 일관된 매핑 사용을 위해 사용."""
    return key.strip().lower().replace(" ", "").replace("-", "")

def handle_exception(error, context=""):
    """공통 에러 핸들링 로직."""
    logger.error(f"{context} - {str(error)}")
    return {"error": str(error)}

async def fetch_logs_from_elasticsearch(es_service, last_timestamp=None, last_sort_key=None, size=100):
    """Elasticsearch에서 주어진 타임스탬프 이후의 로그를 가져오는 함수."""
    if not last_timestamp:
        logger.error("No timestamp provided, skipping log fetch to prevent processing all logs.")
        return [], None

    query = {"range": {"@timestamp": {"gt": last_timestamp}}}
    body = {
        "size": size,
        "sort": [{"@timestamp": "asc"}],
        "query": query,
    }
    if last_sort_key:
        body["search_after"] = [last_sort_key]

    try:
        logs = await es_service.search_logs(
            index=LOGS_INDEX_NAME,
            query=query,
            sort_field="@timestamp",
            sort_order="asc"
        )
        logger.info(f"Fetched {len(logs)} logs from Elasticsearch.")
        return logs, None if not logs else logs[-1].get("sort")
    except ElasticsearchServiceError as e:
        handle_exception(e, "Error fetching logs from Elasticsearch")
        return [], None

@router.get("/events", response_model=PredictionSchema)
async def sse_events(
    bert_service: BERTService = Depends(),
    redis_driver: RedisDriver = Depends(),
    es_service: ElasticsearchService = Depends()
):
    async def event_generator():
        backfilling = True
        last_timestamp = "2024-11-25T00:00:00.000Z"
        last_sort_key = None
        error_count = 0
        max_retries = 3

        latest_log = await es_service.search_logs(
            index=LOGS_INDEX_NAME,
            query={"match_all": {}},
            sort_field="@timestamp",
            sort_order="desc",
            size=1
        )
        max_timestamp = latest_log[0].get("@timestamp") if latest_log else None

        while True:
            try:
                logger.info(f"Fetching logs with last_timestamp: {last_timestamp}, last_sort_key: {last_sort_key}")
                logs, last_sort_key = await fetch_logs_from_elasticsearch(es_service, last_timestamp, last_sort_key)

                if logs:
                    last_timestamp = logs[-1].get("@timestamp", last_timestamp)

                    for log in logs:
                        source_ip = log.get("sourceIPAddress", "unknown")
                        if source_ip == "unknown":
                            logger.warning("Log without sourceIPAddress encountered.")
                            continue

                        try:
                            if await redis_driver.is_processed(source_ip):
                                logger.info(f"Log for {source_ip} already processed. Skipping.")
                                continue
                        except Exception as e:
                            handle_exception(e, f"Error checking if log is processed for IP {source_ip}")
                            continue

                        try:
                            await redis_driver.set_log_queue(source_ip, log, ttl=3600)
                            buffer = await redis_driver.get_log_queue(source_ip)
                            if len(buffer) == BUFFER_SIZE:
                                try:
                                    prediction = await bert_service.predict_attack(buffer)
                                except Exception as e:
                                    handle_exception(e, "BERT prediction error")
                                    prediction = "Prediction Error"

                                logger.info(f"Prediction result: {prediction}")

                                prediction_document = {
                                    "source_ip": source_ip,
                                    "prediction": prediction,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "buffer": buffer
                                }

                                try:
                                    await es_service.save_document("bert-predictions", source_ip, prediction_document)
                                    logger.info(f"Prediction for {source_ip} saved to Elasticsearch.")
                                except Exception as e:
                                    handle_exception(e, "Error saving prediction to Elasticsearch")

                                if prediction and prediction not in ['No Attack', 'Prediction Error']:
                                    normalized_prediction = normalize_key(str(prediction))
                                    tactic = tactics_mapping.get(normalized_prediction, "Unknown Tactic")

                                    attack_document = {
                                        **log,
                                        "mitreAttackTactic": tactic,
                                        "mitreAttackTechnique": normalized_prediction,
                                        "attack_time": datetime.now(timezone(timedelta(hours=9))).isoformat()
                                    }

                                    log_id = f"{source_ip}_{log.get('@timestamp', datetime.now().isoformat())}"
                                    try:
                                        es_service.save_document(ATTACK_INDEX_NAME, log_id, attack_document)
                                        logger.info(f"Document saved to Elasticsearch: {log_id}")
                                    except Exception as e:
                                        handle_exception(e, "Error saving attack document to Elasticsearch")

                                    yield f"data: {json.dumps(attack_document, ensure_ascii=False)}\n\n"
                                    await redis_driver.mark_as_processed(source_ip)

                        except Exception as e:
                            handle_exception(e, f"Error processing log for IP {source_ip}")

                else:
                    if backfilling and (max_timestamp is None or last_timestamp >= max_timestamp):
                        logger.info("Backfill complete. Switching to real-time detection.")
                        backfilling = False
                        last_timestamp = datetime.now(timezone.utc).isoformat()
                    elif not backfilling:
                        logger.info("No new logs fetched. Sleeping briefly.")
                        await asyncio.sleep(5)

            except Exception as e:
                error_count += 1
                handle_exception(e, f"Error in event generator (attempt {error_count}/{max_retries})")
                if error_count >= max_retries:
                    logger.critical("Max retries reached, stopping event generator")
                    break
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(10)
            else:
                error_count = 0
                await asyncio.sleep(1 if logs else 5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")