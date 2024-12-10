from fastapi import Depends, HTTPException
from repositories.report_repository import ReportRepository
from schemas.report_schema import GetAllReportResponseSchema
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
