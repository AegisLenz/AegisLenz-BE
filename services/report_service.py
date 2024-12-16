from fastapi import Depends, HTTPException
from odmantic import ObjectId
from services.gpt_service import GPTService
from repositories.report_repository import ReportRepository
from repositories.bert_repository import BertRepository
from schemas.report_schema import GetAllReportResponseSchema, GetReportResponseSchema, CreateReportTemplateRequestSchema, GetAllReportTemplateResponseSchema, GetReportTemplateResponseSchema
from common.logging import setup_logger

logger = setup_logger()


class ReportService:
    def __init__(self, report_repository: ReportRepository = Depends(), bert_repository: BertRepository = Depends(),
                 gpt_service: GPTService = Depends()):
        self.report_repository = report_repository
        self.bert_repository = bert_repository
        self.gpt_service = gpt_service
        try:
            self.init_prompts = self.gpt_service._load_prompts()
            logger.debug("Successfully loaded initial prompts.")
        except Exception as e:
            logger.error(f"Failed to load initial prompts: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize prompts.")

    async def get_all_report(self, user_id: str) -> GetAllReportResponseSchema:
        try:
            reports = await self.report_repository.find_reports_by_user_id(user_id)
            if not reports:
                logger.warning(f"No reports found for user_id={user_id}")
                return GetAllReportResponseSchema(report_ids=[])
            
            report_ids = [str(report.id) for report in reports]
            logger.info(f"Fetched {len(report_ids)} reports for user_id={user_id}")
            return GetAllReportResponseSchema(report_ids=report_ids)
        except Exception as e:
            logger.error(f"Error in get_all_report for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch reports.")

    async def get_report(self, user_id: str, report_id: ObjectId) -> GetReportResponseSchema:
        try:
            report = await self.report_repository.find_report_by_report_id(report_id)
            if not report:
                logger.error(f"No report found for report_id={report_id}")
                raise HTTPException(status_code=404, detail="No report found for the given report ID")

            return GetReportResponseSchema(
                report_id=report.id,
                title=report.title,
                report_content=report.report_content,
                created_at=report.created_at
            )
        except Exception as e:
            logger.error(f"Error in get_report for report_id {report_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch report.")

    async def create_report_template(self, user_id: str, request: CreateReportTemplateRequestSchema):
        try:
            title, selected_field = request.title, request.selected_field
            return await self.report_repository.create_report_template(user_id, title, selected_field)
        except Exception as e:
            logger.error(f"Error in create_report_template for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create report template.")

    async def get_all_report_template(self, user_id: str) -> GetAllReportTemplateResponseSchema:
        try:
            report_templates = await self.report_repository.find_report_templates_by_user_id(user_id)
            if not report_templates:
                logger.warning(f"No report templates found for user_id={user_id}")
                return GetAllReportTemplateResponseSchema(report_template_ids=[])
            
            report_template_ids = [str(report_template.id) for report_template in report_templates]
            return GetAllReportTemplateResponseSchema(report_template_ids=report_template_ids)
        except Exception as e:
            logger.error(f"Error in get_all_report_template for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch all report template.")

    async def get_report_template(self, user_id: str, report_template_id: ObjectId) -> GetReportTemplateResponseSchema:
        try:
            report_template = await self.report_repository.find_report_template_by_report_template_id(report_template_id)
            if not report_template:
                logger.error(f"No report found for report_template_id={report_template_id}")
                raise HTTPException(status_code=404, detail="No report_template found for the given report template ID")

            return GetReportTemplateResponseSchema(
                title=report_template.title,
                selected_field=report_template.selected_field,
                created_at=report_template.created_at
            )
        except Exception as e:
            logger.error(f"Error in get_report_template for user_id {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch report template.")

    async def create_report(self, user_id: str, report_id: str, report_template_id: str):
        try:
            init_report = await self.report_repository.find_report_by_report_id(report_id)
            if not init_report:
                logger.error(f"No report found for report_id={report_id}")
                raise HTTPException(status_code=404, detail="No report found for the given report ID")

            report_template = await self.report_repository.find_report_template_by_report_template_id(report_template_id)
            if not report_template:
                logger.error(f"No report found for report_template_id={report_template_id}")
                raise HTTPException(status_code=404, detail="No report_template found for the given report template ID")
            
            attack_detection = await self.bert_repository.find_attack_detection(init_report.attack_detection_id)
            if not attack_detection:
                logger.error(f"No attack_detection found for attack_detection_id={attack_detection_id}")
                raise HTTPException(status_code=404, detail="No attack_detection found for the given attack detection ID")
            
            report_content = self.init_prompts["Report"][0]["content"].format(
                logs=attack_detection.attack_logs,
                attack_type=attack_detection.attack_type,
                attack_time=attack_detection.attack_time,
                Field=report_template.selected_field
            )
            report_prompt = [{"role": "system", "content": report_content}]
            report = await self.gpt_service.get_response(report_prompt, json_format=False)

            return await self.report_repository.create_report(title=report_template.title, report_content=report, user_id=user_id,
                                                              attack_detection_id=init_report.attack_detection_id, report_template_id=report_template_id)
        except Exception as e:
            logger.error(f"Error in create_report for report_template_id {report_template_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create report.")
