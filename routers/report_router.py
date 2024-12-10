from fastapi import APIRouter, Depends
from services.report_service import ReportService
from schemas.report_schema import GetAllReportResponseSchema, GetReportResponseSchema

router = APIRouter(prefix="/report", tags=["report"])

@router.get("/", response_model=GetAllReportResponseSchema)
async def get_all_report(user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.get_all_report(user_id)


@router.get("/{report_id}", response_model=GetReportResponseSchema)
async def get_report(report_id: str, user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.get_report(user_id, report_id)
