from fastapi import Depends, HTTPException
from repositories.report_repository import ReportRepository
from schemas.report_schema import GetAllReportResponseSchema, GetReportResponseSchema, CreateReportTemplateRequestSchema, GetAllReportTemplateResponseSchema
from common.logging import setup_logger

logger = setup_logger()


class ReportService:
    def __init__(self, report_repository: ReportRepository = Depends()):
        self.report_repository = report_repository

    async def get_all_report(self, user_id: str) -> GetAllReportResponseSchema:
        reports = await self.report_repository.find_reports_by_user_id(user_id)
        if not reports:
            logger.warning(f"No reports found for user_id={user_id}")
            return GetAllReportResponseSchema(report_ids=[])
        
        report_ids = [str(report.id) for report in reports]
        return GetAllReportResponseSchema(report_ids=report_ids)

    async def get_report(self, user_id: str, report_id: str) -> GetReportResponseSchema:
        report = await self.report_repository.find_report_by_report_id(report_id)
        if not report:
            logger.warning(f"No report found for report_id={report_id}")
            raise HTTPException(status_code=404, detail="No report found for the given report ID")

        return GetReportResponseSchema(
            report_id=report.id,
            title=report.title,
            report_content=report.report_content,
            created_at=report.created_at
        )

    async def create_report_template(self, user_id: str, request: CreateReportTemplateRequestSchema):
        title, selected_field, prompt_text = request.title, request.selected_field, request.prompt_text
        return await self.report_repository.create_report_template(user_id, title, selected_field, prompt_text)

    async def get_all_report_template(self, user_id: str) -> GetAllReportTemplateResponseSchema:
        report_templates = await self.report_repository.find_report_templates_by_user_id(user_id)
        if not report_templates:
            logger.warning(f"No report templates found for user_id={user_id}")
            return GetAllReportTemplateResponseSchema(report_template_ids=[])
        
        report_template_ids = [str(report_template.id) for report_template in report_templates]
        return GetAllReportTemplateResponseSchema(report_template_ids=report_template_ids)
