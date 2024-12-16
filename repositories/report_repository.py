from fastapi import HTTPException
from typing import Optional
from odmantic import ObjectId
from datetime import datetime, timedelta, timezone
from database.mongodb_driver import mongodb
from models.attack_detection_model import Report, ReportTemplate
from common.logging import setup_logger

logger = setup_logger()


class ReportRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

    async def find_reports_by_user_id(self, user_id: str) -> list:
        try:
            reports = await self.mongodb_engine.find(
                Report,
                Report.user_id == user_id,
                sort=(Report.created_at, Report.created_at.desc())
            )
            return reports
        except Exception as e:
            logger.error(f"Error fetching reports for user_id={user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch reports: {str(e)}")

    async def find_report_by_attack_detection(self, attack_detection_id: str) -> Report:
        try:
            report = await self.mongodb_engine.find_one(
                Report,
                Report.attack_detection_id == ObjectId(attack_detection_id)
            )
            return report
        except Exception as e:
            logger.error(f"Error fetching report for attack_detection_id={attack_detection_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch report: {str(e)}")

    async def find_report_by_report_id(self, report_id: str) -> Report:
        try:
            report = await self.mongodb_engine.find_one(
                Report,
                Report.id == ObjectId(report_id)
            )
            return report
        except Exception as e:
            logger.error(f"Error fetching report for report_id={report_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch report: {str(e)}")

    async def create_report_template(self, user_id: str, title: str, selected_field: list) -> ObjectId:
        try:
            report_template = ReportTemplate(
                title=title,
                selected_field=selected_field,
                user_id=user_id
            )
            result = await self.mongodb_engine.save(report_template)
            return result.id
        except Exception as e:
            logger.error(f"Error creating report template for user ID '{user_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save the report template: {str(e)}")

    async def find_report_templates_by_user_id(self, user_id: str) -> list:
        try:
            report_templates = await self.mongodb_engine.find(
                ReportTemplate,
                ReportTemplate.user_id == user_id
            )
            return report_templates
        except Exception as e:
            logger.error(f"Error fetching report templates for user_id={user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch report templates: {str(e)}")

    async def find_report_template_by_report_template_id(self, report_template_id: ObjectId) -> ReportTemplate:
        try:
            report_template = await self.mongodb_engine.find_one(
                ReportTemplate,
                ReportTemplate.id == ObjectId(report_template_id),
                sort=(ReportTemplate.created_at, ReportTemplate.created_at.desc())
            )
            return report_template
        except Exception as e:
            logger.error(f"Error fetching report template for report_template_id={report_template_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch report template: {str(e)}")

    async def create_report(self, report_content: str, user_id: str, attack_detection_id: ObjectId,
                            title: Optional[str] = None, report_template_id: Optional[ObjectId] = None) -> ObjectId:
        try:
            report = Report(
                title=title,
                report_content=report_content,
                user_id=user_id,
                attack_detection_id=attack_detection_id,
                report_template_id=report_template_id,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            result = await self.mongodb_engine.save(report)
            return result.id
        except Exception as e:
            logger.error(f"Error creating report template for user ID '{user_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save the report template: {str(e)}")
