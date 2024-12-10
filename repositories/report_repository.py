from fastapi import HTTPException
from odmantic import ObjectId
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
                Report.user_id == user_id
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

    async def create_report_template(self, user_id, title, selected_field, prompt_text):
        try:
            report_template = ReportTemplate(
                title=title,
                selected_field=selected_field,
                prompt_text=prompt_text,
                user_id=user_id
            )
            result = await self.mongodb_engine.save(report_template)
            return result.id
        except Exception as e:
            logger.error(f"Error creating report template for user ID '{user_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save the report template: {str(e)}")
