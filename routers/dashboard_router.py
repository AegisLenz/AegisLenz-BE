from fastapi import APIRouter, Depends
from services.dashboard_service import DashboardService
from schemas.dashboard_schema import AccountByServiceResponseSchema, AccountCountResponseSchema, DetectionResponseSchema

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
