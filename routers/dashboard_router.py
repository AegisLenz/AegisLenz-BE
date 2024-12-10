from fastapi import APIRouter, Depends
from services.dashboard_service import DashboardService
from schemas.dashboard_schema import AccountByServiceResponseSchema, AccountCountResponseSchema, DetectionResponseSchema, ScoreResponseSchema, RisksResponseSchema, ReportCheckResponseSchema

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/account-by-service", response_model=AccountByServiceResponseSchema)
async def get_account_by_service(user_id: str = "1", dashboard_service: DashboardService = Depends()):
    return await dashboard_service.get_account_by_service(user_id)

@router.get("/account-count", response_model=AccountCountResponseSchema)
async def get_account_count(user_id: str = "1", dashboard_service: DashboardService = Depends()):
    return await dashboard_service.get_account_count(user_id)

@router.get("/detection", response_model=DetectionResponseSchema)
def get_detection(user_id: str = "1", dashboard_service: DashboardService = Depends()):
    return dashboard_service.get_detection(user_id)

@router.get("/score", response_model=ScoreResponseSchema)
async def get_score(user_id: str = "1", dashboard_service: DashboardService = Depends()):
    return await dashboard_service.get_score(user_id)

@router.get("/risks", response_model=RisksResponseSchema)
async def get_risks(user_id: str = "1", dashboard_service: DashboardService = Depends()):
    return await dashboard_service.get_risks(user_id)

@router.get("/report-check", response_model=ReportCheckResponseSchema)
async def get_report_check(user_id: str = "1", dashboard_service: DashboardService = Depends()):
    return await dashboard_service.get_report_check(user_id)
