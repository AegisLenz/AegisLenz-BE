from fastapi import Depends, HTTPException
from repositories.report_repository import ReportRepository
from schemas.report_schema import GetAllReportResponseSchema, GetReportResponseSchema
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
