from fastapi import APIRouter, Depends
from services.bert_service import BERTService
from collections import deque

router = APIRouter(prefix="/bert", tags=["IAMBERT"])

# 로그를 저장할 버퍼 (최대 크기 5)
log_buffer = deque(maxlen=5)

@router.post("/predict")
def predict_attack(log_data: dict, bert_service: BERTService = Depends(BERTService)):
    log_buffer.append(log_data)
    
    if len(log_buffer) == 5:
        return bert_service.predict_attack(list(log_buffer))