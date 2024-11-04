from fastapi import HTTPException
from core.mongodb_driver import mongodb

class AssetRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client
    
    async def save_asset(self, user_asset) -> None:
        try:
            await self.mongodb_engine.save(user_asset)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")