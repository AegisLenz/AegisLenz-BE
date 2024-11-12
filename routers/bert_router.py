import os
import json
import asyncio
from collections import deque
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

# Elasticsearch 클라이언트 설정
es_host = os.getenv("ES_HOST", "http://localhost")
es_port = os.getenv("ES_PORT", "9200")
es_index = os.getenv("ES_INDEX", "cloudtrail-logs-*")
es = Elasticsearch(f"{es_host}:{es_port}", max_retries=10, retry_on_timeout=True, request_timeout=120)

# API 라우터 설정
router = APIRouter(prefix="/bert", tags=["bert"])

# 로그를 저장할 버퍼 (최대 크기 5)
log_buffer = deque(maxlen=5)

# Elasticsearch에서 로그 데이터를 가져오는 함수
async def fetch_logs_from_elasticsearch():
    try:
        response = es.search(
            index=es_index,  # .env에서 불러온 인덱스 이름 사용
            body={
                "size": 5,
                "sort": [{"@timestamp": {"order": "desc"}}],
                "query": {"match_all": {}}
            }
        )
        logs = [hit["_source"] for hit in response["hits"]["hits"]]
        print(f"Fetched {len(logs)} logs from Elasticsearch.")
        return logs
    except Exception as e:
        print(f"Error fetching logs from Elasticsearch: {str(e)}")
        return []

@router.post("/predict")
async def predict_attack(log_data: dict):
    # 사용되지 않는 API일 경우 코드 주석 처리 또는 제거
    # log_buffer.append(log_data)
    # print(f"Added new log to buffer. Current buffer size: {len(log_buffer)}")
    return {"status": "API not used"}  # 응답을 수정하여 명확히 표시

@router.get("/events", response_model=PredictionSchema)
async def sse_events(bert_service: BERTService = Depends(BERTService)):
    async def event_generator():
        while True:
            try:
                # Elasticsearch에서 최근 로그 가져오기
                logs = await fetch_logs_from_elasticsearch()
                if logs:
                    log_buffer.extend(logs[:5])  # 최대 5개의 로그만 유지
                    print(f"Log buffer extended. Current buffer size: {len(log_buffer)}")

                # 버퍼가 5개로 가득 차면 예측 실행
                if len(log_buffer) == 5:
                    prediction = await bert_service.predict_attack(list(log_buffer))
                    print(f"Prediction result: {prediction}")

                    # 예측 결과가 'No Attack'이 아닌 경우에만 SSE 전송
                    if prediction != 'No Attack':
                        response = PredictionSchema(is_attack=True, prediction=prediction)
                        yield f"data: {json.dumps(response.dict(), ensure_ascii=False)}\n\n"
                else:
                    # 데이터가 부족할 경우 SSE 이벤트를 전송하지 않고 대기
                    print("Buffer does not contain enough data for prediction. Waiting for more logs.")

            except Exception as e:
                print(f"Error in event generator: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            await asyncio.sleep(5)  # 5초마다 로그를 가져와서 처리

    return StreamingResponse(event_generator(), media_type="text/event-stream")