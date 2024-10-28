import json
import asyncio
from collections import deque
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from elasticsearch import Elasticsearch

# Elasticsearch 클라이언트 설정
es = Elasticsearch("http://23.23.93.131:9200", max_retries=10, retry_on_timeout=True, request_timeout=120)

# API 라우터 설정
router = APIRouter(prefix="/bert", tags=["bert"])

# 로그를 저장할 버퍼 (최대 크기 5)
log_buffer = deque(maxlen=5)

# Elasticsearch에서 로그 데이터를 가져오는 함수
async def fetch_logs_from_elasticsearch():
    try:
        # 최신 로그 데이터를 5개 가져오기
        response = es.search(
            index="cloudtrail-logs-*",  # 패턴에 맞는 인덱스에서 검색
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
    try:
        log_buffer.append(log_data)  # 로그 데이터를 버퍼에 저장
        print(f"Added new log to buffer. Current buffer size: {len(log_buffer)}")
        return {"status": "log received"}  # 데이터가 정상 수신됨을 응답
    except Exception as e:
        # 예외 발생 시 에러 메시지를 반환
        print(f"Error adding log to buffer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events", response_model=PredictionSchema)
async def sse_events(bert_service: BERTService = Depends(BERTService)):
    async def event_generator():
        while True:
            try:
                # Elasticsearch에서 최근 로그 가져오기
                logs = await fetch_logs_from_elasticsearch()
                
                if logs:
                    log_buffer.extend(logs)
                    print(f"Log buffer extended. Current buffer size: {len(log_buffer)}")

                # 버퍼가 5개로 가득 차면 예측 실행
                if len(log_buffer) == 5:
                    prediction = await bert_service.predict_attack(list(log_buffer))
                    print(f"Prediction result: {prediction}")
                else:
                    prediction = 'Not enough data yet'  # 충분한 데이터가 없으면 대기

                # 예측 결과가 'No Attack'이 아니면, SSE로 전송
                if prediction != 'No Attack':
                    response = PredictionSchema(is_attack=True, prediction=prediction)
                    yield f"data: {json.dumps(response.dict(), ensure_ascii=False)}\n\n"

                # 예측 후 버퍼 비움
                log_buffer.clear()

            except Exception as e:
                print(f"Error in event generator: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            await asyncio.sleep(5)  # 5초마다 로그를 가져와서 처리

    return StreamingResponse(event_generator(), media_type="text/event-stream")