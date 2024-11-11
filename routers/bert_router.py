import os
import json
import asyncio
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from dotenv import load_dotenv
from core.redis_driver import RedisDriver

# 환경 변수 로드
load_dotenv()

# Elasticsearch 클라이언트 설정
es_host = os.getenv("ES_HOST", "http://localhost")
es_port = os.getenv("ES_PORT", "9200")
es_index = os.getenv("ES_INDEX", "cloudtrail-logs-*")
es = Elasticsearch(f"{es_host}:{es_port}", max_retries=10, retry_on_timeout=True, request_timeout=120)

# RedisDriver 설정
redis_driver = RedisDriver()

# API 라우터 설정
router = APIRouter(prefix="/bert", tags=["bert"])

# Elasticsearch에서 로그 데이터를 가져오는 함수
async def fetch_logs_from_elasticsearch():
    try:
        response = es.search(
            index=es_index,  # .env에서 불러온 인덱스 이름 사용
            body={
                "size": 10,
                "sort": [{"@timestamp": {"order": "desc"}}],
                "query": {"match_all": {}}
            }
        )
        logs = [hit["_source"] for hit in response["hits"]["hits"]]
        print(f"Elasticsearch에서 {len(logs)}개의 로그를 가져왔습니다.")
        return logs
    except es_exceptions.ConnectionError as e:
        print(f"Elasticsearch 연결 오류: {str(e)}")
        return []
    except es_exceptions.RequestError as e:
        print(f"Elasticsearch 요청 오류: {str(e)}")
        return []
    except Exception as e:
        print(f"Elasticsearch에서 로그를 가져오는 중 오류 발생: {str(e)}")
        return []

@router.get("/events", response_model=PredictionSchema)
async def sse_events(bert_service: BERTService = Depends(BERTService)):
    async def event_generator():
        while True:
            try:
                # Elasticsearch에서 최근 로그 가져오기
                logs = await fetch_logs_from_elasticsearch()
                if logs:
                    for log in logs:
                        source_ip = log.get("sourceIPAddress")
                        if source_ip:
                            # Redis에 로그를 sourceIP 별로 추가
                            await redis_driver.add_log_to_buffer(source_ip, log)
                            print(f"{source_ip}의 로그가 Redis에 추가되었습니다.")

                # Redis에서 모든 로그 버퍼 가져오기
                buffers = await redis_driver.get_all_buffers()
                
                # 각 sourceIP에 대해 로그 버퍼가 5개 이상인 경우 예측 실행
                for source_ip, buffer in buffers.items():
                    if len(buffer) == 5:
                        prediction = await bert_service.predict_attack(buffer)
                        print(f"{source_ip}에 대한 예측 결과: {prediction}")

                        # 예측 결과가 공격일 경우에만 SSE 전송
                        if prediction != 'No Attack':
                            response = PredictionSchema(is_attack=True, prediction=prediction)
                            yield f"data: {json.dumps(response.dict(), ensure_ascii=False)}\n\n"

            except Exception as e:
                print(f"이벤트 생성기에서 오류 발생: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            await asyncio.sleep(5)  # 5초마다 로그를 처리

    return StreamingResponse(event_generator(), media_type="text/event-stream")
