from fastapi import APIRouter, Depends
from services.report_service import ReportService

router = APIRouter(prefix="/report", tags=["report"])

@router.get("/")
async def get_all_report(user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.get_all_report(user_id)
