import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema
from schemas.prompt_schema import CreatePromptResponseSchema
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from dotenv import load_dotenv
from core.redis_driver import RedisDriver

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
router = APIRouter(prefix="/bert", tags=["bert"])

async def fetch_logs_from_elasticsearch():
    """
    Elasticsearch에서 최근 5개의 로그를 가져오는 함수
    """
    try:
        response = es.search(
            index=es_index,
            body={
                "size": 5,  # 5개의 로그를 가져옴
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
                # Elasticsearch에서 최근 5개의 로그 가져오기
                logs = await fetch_logs_from_elasticsearch()
                if logs:
                    for log in logs:
                        source_ip = log.get("sourceIPAddress")
                        if source_ip:
                            try:
                                await redis_driver.set_log_queue(source_ip, log)
                                print(f"{source_ip}의 로그가 Redis에 추가되었습니다.")
                            except Exception as redis_error:
                                print(f"Redis에 로그 추가 중 오류 발생: {str(redis_error)}")
                                continue

                for source_ip in {log.get("sourceIPAddress") for log in logs if log.get("sourceIPAddress")}:
                    try:
                        buffer = await redis_driver.get_log_queue(source_ip)
                        if len(buffer) == 5:
                            prediction = await bert_service.predict_attack(buffer)
                            print(f"{source_ip}에 대한 예측 결과: {prediction}")

                            if prediction != 'No Attack':
                                attack_info = {}
                                attack_info['attack_time'] = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()
                                attack_info['attack_type'] = ["TA0007 - Discovery", prediction]
                                attack_info["logs"] = buffer
                                prompt_session_id = await bert_service.process_after_detection("1", attack_info)
                                response = PredictionSchema(
                                    is_attack=True,
                                    technique=prediction,
                                    tactic="TA0007 - Discovery",
                                    prompt_session_id=prompt_session_id
                                )
                                yield f"data: {json.dumps(response.dict(), ensure_ascii=False)}\n\n"

                            await redis_driver.log_prediction(source_ip, response.dict())
                    except Exception as e:
                        print(f"{source_ip}의 예측 처리 중 오류 발생: {str(e)}")
                        continue
            except Exception as e:
                print(f"이벤트 생성기에서 오류 발생: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            
            await asyncio.sleep(5)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/test")
async def test(bert_service: BERTService = Depends(BERTService)):
    attack_info = {}
    attack_info['attack_time'] = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()
    attack_info['attack_type'] = ["T1087 - Account Discovery", "TA0007 - Discovery"]

    file_path = "./temp_files/logs.txt"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            attack_info['logs'] = file.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"File not found: {file_path}")

    prompt_session_id = await bert_service.process_after_detection("1", attack_info)
    return CreatePromptResponseSchema(prompt_session_id=prompt_session_id)
