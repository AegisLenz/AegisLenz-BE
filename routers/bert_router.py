from fastapi import APIRouter, Depends
from services.bert_service import BERTService
from typing import List

router = APIRouter(prefix="/bert", tags=["IAMBERT"])

@router.post("/predict")
def predict_attack(log_data: List[dict], bert_service: BERTService = Depends(BERTService)):
    return bert_service.predict_attack(log_data)