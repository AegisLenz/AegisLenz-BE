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

attack_index_name = "cloudtrail-attack-logs"

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
    """
    키를 정규화하여 일관된 매핑 사용을 위해 사용.
    """
    return key.strip().lower().replace(" ", "").replace("-", "")

async def fetch_logs_from_elasticsearch(es_service, last_timestamp=None, last_sort_key=None):
    """
    Elasticsearch에서 주어진 타임스탬프 이후의 로그를 가져오는 함수.
    """
    if not last_timestamp:
        logger.error("No timestamp provided, skipping log fetch to prevent processing all logs.")
        return [], None

    query = {"range": {"@timestamp": {"gt": last_timestamp}}}
    body = {
        "size": 5,
        "sort": [{"@timestamp": "asc"}],
        "query": query,
    }
    if last_sort_key:
        body["search_after"] = [last_sort_key]

    try:
        logs = es_service.search_logs(
            index=os.getenv("ES_INDEX", "cloudtrail-logs-*"),
            query=query,
            sort_field="@timestamp",
            sort_order="asc"
        )
        return logs, None if not logs else logs[-1].get("sort")
    except ElasticsearchServiceError as e:
        logger.error(f"Error fetching logs from Elasticsearch: {str(e)}")
        return [], None

@router.get("/events", response_model=PredictionSchema)
async def sse_events(bert_service: BERTService = Depends(BERTService)):
    async def event_generator():
        last_timestamp = None
        last_sort_key = None
        error_count = 0
        max_retries = 3

        while True:
            try:
                logs, last_sort_key = await fetch_logs_from_elasticsearch(es_service, last_timestamp, last_sort_key)
                if logs:
                    last_timestamp = logs[-1].get("@timestamp")

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
                            logger.error(f"Error checking processed status for {source_ip}: {str(e)}")
                            continue

                        try:
                            await redis_driver.set_log_queue(source_ip, log)
                            buffer = await redis_driver.get_log_queue(source_ip)
                            if len(buffer) == 5:
                                prediction = await bert_service.predict_attack(buffer)
                                normalized_prediction = normalize_key(str(prediction))
                                tactic = tactics_mapping.get(normalized_prediction, "Unknown Tactic")

                                if prediction != 'No Attack':
                                    attack_document = {
                                        **log,
                                        "mitreAttackTactic": tactic,
                                        "mitreAttackTechnique": str(normalized_prediction),
                                        "attack_time": datetime.now(timezone(timedelta(hours=9))).isoformat()
                                    }

                                    log_id = f"{source_ip}_{log.get('@timestamp', datetime.now().isoformat())}"
                                    try:
                                        es_service.save_document(attack_index_name, log_id, attack_document)
                                        logger.info(f"Document saved to Elasticsearch: {log_id}")

                                        user_id = "1"
                                        attack_info = {
                                            "attack_time": attack_document["attack_time"],
                                            "attack_type": [tactic],
                                            "logs": json.dumps(attack_document)
                                        }
                                        try:
                                            prompt_session_id = await bert_service.process_after_detection(user_id, attack_info)
                                            logger.info(f"Session ID {prompt_session_id} generated for user {user_id}.")
                                        except Exception as e:
                                            logger.error(f"Error in process_after_detection for user {user_id}: {e}")
                                    except ElasticsearchServiceError as e:
                                        logger.error(f"Failed to save document for {source_ip}: {str(e)}")
                                    yield f"data: {json.dumps(attack_document, ensure_ascii=False)}\n\n"
                                    await redis_driver.mark_as_processed(source_ip)
                        except Exception as e:
                            logger.error(f"Error processing log for {source_ip}: {str(e)}")
                else:
                    logger.info("No new logs fetched. Sleeping briefly.")
                    await asyncio.sleep(1)

            except Exception as e:
                error_count += 1
                logger.error(f"Error in event generator (attempt {error_count}/{max_retries}): {str(e)}")
                if error_count >= max_retries:
                    logger.critical("Max retries reached, stopping event generator")
                    break
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(10)
            else:
                error_count = 0
                await asyncio.sleep(5 if not logs else 0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")