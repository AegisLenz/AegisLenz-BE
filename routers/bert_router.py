import os
import re
import asyncio
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from services.bert_service import BERTService
from database.redis_driver import RedisDriver
from services.es_service import ElasticsearchService
from common.logging import setup_logger
from uuid import uuid4

logger = setup_logger()

router = APIRouter(prefix="/bert", tags=["bert"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
COMMON_DIR = os.path.join(PROJECT_ROOT, "common")

TACTICS_MAPPING_FILE = os.path.join(COMMON_DIR, "tactics_mapping.json")
ELASTICSEARCH_MAPPING_FILE = os.path.join(COMMON_DIR, "elasticsearch_mapping.json")

def get_es_service(request: Request) -> ElasticsearchService:
    return request.app.state.es_service

def get_redis_driver(request: Request) -> RedisDriver:
    return request.app.state.redis_driver

def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Failed to load JSON file: {file_path}, Error: {e}")
        return {}

tactics_mapping = load_json(TACTICS_MAPPING_FILE)

BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", 1))
ES_INDEX = os.getenv("ES_INDEX")
ES_ATTACK_INDEX = os.getenv("ES_ATTACK_INDEX")

if not ES_INDEX or not ES_ATTACK_INDEX:
    raise ValueError("Environment variables 'ES_INDEX' and 'ES_ATTACK_INDEX' must be set.")

def normalize_key(key: str) -> str:
    match = re.match(r"(t\d+)([a-z]+)", key, re.I)
    if not match:
        return key

    technique_id = match.group(1).upper()
    description = re.sub(r"([a-z])([A-Z])", r"\1 \2", match.group(2)).title()

    return f"{technique_id} - {description}"

@router.get(
    "/events",
    response_class=StreamingResponse,
    summary="Stream attack events via SSE",
)
async def sse_events(request: Request, bert_service: BERTService = Depends(), 
                     redis_driver: RedisDriver = Depends(get_redis_driver), 
                     es_service: ElasticsearchService = Depends(get_es_service)):
    async def event_generator():
        backfilling = True
        last_timestamp = datetime.now(timezone.utc) - timedelta(days=1)
        last_sort_key = None

        dynamic_sleep_interval = 1

        while True:
            if await request.is_disconnected():
                logger.info("Client disconnected from SSE stream.")
                break

            try:
                logs, last_sort_key = await fetch_logs_from_elasticsearch(es_service, last_timestamp, last_sort_key)

                if logs:
                    last_timestamp = datetime.fromisoformat(logs[-1]["@timestamp"])
                    dynamic_sleep_interval = 1

                    tasks = [
                        process_log(log["sourceIPAddress"], log, redis_driver, bert_service, es_service)
                        for log in logs if log.get("sourceIPAddress") and not await redis_driver.is_processed(log.get("sourceIPAddress"))
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if result:
                            yield f"data: {json.dumps(result)}\n\n"
                else:
                    backfilling = False

                await asyncio.sleep(dynamic_sleep_interval)

            except asyncio.CancelledError:
                logger.info("Client disconnected from SSE stream.")
                break
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                dynamic_sleep_interval = min(dynamic_sleep_interval * 2, 10)
                await asyncio.sleep(dynamic_sleep_interval)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def fetch_logs_from_elasticsearch(es_service, last_timestamp, last_sort_key):
    try:
        logs = await es_service.search_logs(
            index=ES_INDEX,
            query={"range": {"@timestamp": {"gte": last_timestamp}}},
            sort_field="@timestamp",
            sort_order="asc",
            size=100
        )
        #logger.info(f"Fetched logs: {logs}")
        return logs, None if not logs else logs[-1].get("sort")
    except Exception as e:
        logger.error(f"Failed to fetch logs: {e}")
        return [], None


async def process_log(source_ip, log, redis_driver, bert_service, es_service):
    """
    개별 로그를 처리하는 함수.
    Redis에 로그를 저장하고, 버퍼 크기 도달 시 BERT 모델로 예측 후 공격으로 판정되면 Elasticsearch에 저장.
    """
    try:
        await redis_driver.set_log_queue(source_ip, log)

        buffer = await redis_driver.get_log_queue(source_ip)

        if len(buffer) >= BUFFER_SIZE:
            logger.info(f"Buffer size reached for {source_ip}: {len(buffer)} logs")

            prediction = await bert_service.predict_attack(buffer)
            logger.info(f"Prediction for {source_ip}: {prediction}")

            if prediction != "No Attack":
                return await process_and_store_attack(es_service, redis_driver, source_ip, log, prediction)

        return None
    except Exception as e:
        logger.error(f"Error processing log for {source_ip}: {e}", exc_info=True)
        return None

async def process_and_store_attack(es_service, redis_driver, source_ip, log, prediction):
    try:
        logger.info(f"Processing log: {log}")
        normalized_prediction = normalize_key(prediction)
        tactic = tactics_mapping.get(normalized_prediction, "Unknown Tactic")
        logger.info(f"Tactic mapped: {tactic}")

        attack_data = {
            "mitreAttackTechnique": normalized_prediction,
            "mitreAttackTactic": tactic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_session_id": log.get("sharedEventId") or log.get("eventId") or str(uuid4())
        }

        log_id = f"{source_ip}_{log.get('@timestamp', datetime.now(timezone.utc).isoformat())}_{uuid4()}"
        await es_service.save_document(
            index=ES_ATTACK_INDEX,
            doc_id=log_id,
            body=attack_data
        )
        await redis_driver.mark_as_processed(source_ip)
        return attack_data
    except Exception as e:
        logger.error(f"Failed to process and store attack: {e}")
        return None