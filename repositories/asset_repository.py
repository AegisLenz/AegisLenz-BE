from fastapi import HTTPException
from database.mongodb_driver import mongodb
from models.asset_model import UserAsset


class AssetRepository:
    def __init__(self):
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client
    
    async def save_asset(self, user_asset) -> None:
        try:
            await self.mongodb_engine.save(user_asset)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save the asset: {str(e)}")

    async def update_asset(self, user_id, asset) -> None:
        try:
            # 기존 UserAsset 조회
            existing_asset = await self.mongodb_engine.find_one(
                UserAsset,
                UserAsset.user_id == user_id
            )
            if not existing_asset:
                raise HTTPException(status_code=404, detail=f"No asset found with user_id: {user_id}")
            
            # 기존 자산 업데이트
            existing_asset.asset = asset
            await self.mongodb_engine.save(existing_asset)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update the asset: {str(e)}")

    async def find_asset_by_user_id(self, user_id) -> UserAsset:
        try:
            user_assets = await self.mongodb_engine.find_one(
                UserAsset,
                UserAsset.user_id == user_id
            )
            return user_assets
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch assets: {str(e)}")
