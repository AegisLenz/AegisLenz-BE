import json
import asyncio
from collections import deque
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from services.bert_service import BERTService
from schemas.bert_schema import PredictionSchema

router = APIRouter(prefix="/bert", tags=["bert"])

# 로그를 저장할 버퍼 (최대 크기 5)
log_buffer = deque(maxlen=5)

@router.post("/predict")
def predict_attack(log_data: dict):
    log_buffer.append(log_data)


@router.get("/events", response_model=PredictionSchema)
async def sse_events(bert_service: BERTService = Depends(BERTService)):
    async def event_generator():
        while True:
            if len(log_buffer) == 5:
                prediction = await bert_service.predict_attack(list(log_buffer))
                if not prediction == 'No Attack':
                    response = PredictionSchema(is_attack=True, prediction=prediction)
                    yield json.dumps(response.dict(), ensure_ascii=False) + "\n"
                
                log_buffer.popleft()
            
            await asyncio.sleep(1)  # 1초마다 체크
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")