import os
import json
import datetime
from odmantic import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from models.policy_model import Policy
from core.redis_driver import RedisDriver
from core.mongodb_driver import mongodb

load_dotenv()

class PolicyRepository:
    def __init__(self):
        self.redis_client = RedisDriver()
        self.mongodb_engine = mongodb.engine

    async def find_policy(self, service, event_name):
        try:
            return await self.mongodb_engine.find_one(Policy, Policy.service == service and Policy.event_name == event_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
