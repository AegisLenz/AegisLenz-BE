from fastapi import APIRouter, Depends, Body
from services.report_service import ReportService
from schemas.report_schema import GetAllReportResponseSchema, GetReportResponseSchema, CreateReportTemplateRequestSchema, GetAllReportTemplateResponseSchema, GetReportTemplateResponseSchema

router = APIRouter(prefix="/report", tags=["report"])

@router.get("/", response_model=GetAllReportResponseSchema)
async def get_all_report(user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.get_all_report(user_id)


@router.get("/{report_id}", response_model=GetReportResponseSchema)
async def get_report(report_id: str, user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.get_report(user_id, report_id)


@router.post("/template/")
async def create_report_template(user_id: str = "1", request: CreateReportTemplateRequestSchema = Body(...), report_service: ReportService = Depends()):
    return await report_service.create_report_template(user_id, request)


@router.get("/template/", response_model=GetAllReportTemplateResponseSchema)
async def get_all_report_template(user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.get_all_report_template(user_id)


@router.get("/template/{report_template_id}", response_model=GetReportTemplateResponseSchema)
async def get_report_template(report_template_id: str, user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.get_report_template(user_id, report_template_id)


@router.post("/{report_id}/{report_template_id}")
async def create_report(report_id: str, report_template_id: str, user_id: str = "1", report_service: ReportService = Depends()):
    return await report_service.create_report(user_id, report_id, report_template_id)
