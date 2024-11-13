import os
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from elasticsearch import Elasticsearch, TransportError
from dotenv import load_dotenv
from core.redis_driver import RedisDriver
from datetime import datetime

# 환경 변수 로드
load_dotenv()

# Elasticsearch 클라이언트 설정
es_host = os.getenv("ES_HOST", "http://23.23.93.131")
es_port = os.getenv("ES_PORT", "9200")
es_index = os.getenv("ES_INDEX", "cloudtrail-logs-*")
es = Elasticsearch(f"{es_host}:{es_port}", max_retries=10, retry_on_timeout=True, request_timeout=120)

# API 라우터 설정
router = APIRouter(prefix="/bert", tags=["bert"])

# Redis 드라이버 인스턴스
redis_driver = RedisDriver()

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
        print(f"Fetched logs from Elasticsearch: {logs}")
        return logs
    except Exception as e:
        print(f"Error fetching logs from Elasticsearch: {e}")
        await asyncio.sleep(2)  # 오류 발생 시 재시도를 위한 대기
        return []

@router.get("/events", response_model=PredictionSchema)
async def sse_events(bert_service: BERTService = Depends(BERTService)):
    async def event_generator():
        while True:
            try:
                logs = await fetch_logs_from_elasticsearch()
                for log in logs:
                    source_ip = log.get("sourceIPAddress")
                    print(f"Processing log with source IP: {source_ip}")
                    if source_ip:
                        await redis_driver.set_log_queue(source_ip, log)
                        print(f"Log added for IP: {source_ip} in Redis.")

                        # Redis에서 특정 IP의 로그 큐를 가져와 상태 확인
                        ip_logs = await redis_driver.get_log_queue(source_ip)
                        print(f"Current log queue for IP {source_ip}: {ip_logs}")

                        # 큐가 5개로 가득 차면 BERT 예측 실행
                        if len(ip_logs) == 5:
                            attack_count = sum(
                                1 for log_event in ip_logs if bert_service.predict(log_event) != "No Attack"
                            )

                            # 과반수가 공격으로 예측되면 경고 전송
                            if attack_count >= 3:
                                prediction_data = {
                                    "is_attack": True,
                                    "prediction": "T1098 - Account Manipulation",
                                    "timestamp": datetime.utcnow().isoformat()
                                }

                                # Redis에 예측 결과 저장
                                await redis_driver.log_prediction(source_ip, prediction_data)

                                # Elasticsearch에 예측 결과 저장
                                try:
                                    es.index(
                                        index="prediction-logs",
                                        document={
                                            "source_ip": source_ip,
                                            "prediction": prediction_data["prediction"],
                                            "timestamp": prediction_data["timestamp"]
                                        }
                                    )
                                    print(f"Logged prediction to Elasticsearch for IP {source_ip}")
                                except Exception as es_error:
                                    print(f"Error logging prediction to Elasticsearch: {es_error}")

                                yield f"data: {json.dumps(prediction_data, ensure_ascii=False)}\n\n"
                        else:
                            print(f"Not enough logs for prediction for IP {source_ip}. Waiting for more logs.")

            except Exception as e:
                print(f"Error in event generator: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            await asyncio.sleep(2 if len(logs) > 5 else 5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
