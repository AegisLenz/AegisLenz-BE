from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from database.mongodb_driver import mongodb
from models.user_model import Dashboard
from common.logging import setup_logger

logger = setup_logger()


class DashboardRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client
    
    async def find_dashboard(self, user_id: str) -> Dashboard:
        try:
            dashboard = await self.mongodb_engine.find_one(
                Dashboard,
                Dashboard.user_id == user_id,
                sort=(Dashboard.created_at, Dashboard.created_at.desc())
            )
            return dashboard
        except Exception as e:
            logger.error(f"Error retrieving dashboard for user ID '{user_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve dashbiard for user ID '{user_id}': {str(e)}")

    async def save_dashboard(self, daily_insight: str, user_id: str) -> None:
        try:
            dashboard = Dashboard(
                daily_insight=daily_insight,
                user_id=user_id,
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            await self.mongodb_engine.save(dashboard)
            logger.info(f"Successfully saved dashboard for user ID '{user_id}' with created_at: {dashboard.created_at}")
        except Exception as e:
            logger.error(f"Error saving daily insight for user ID '{user_id}', Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save daily insight: {e}")
