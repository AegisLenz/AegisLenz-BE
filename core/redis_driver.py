import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()
redis_host = os.getenv("REDIS_HOST")

class RedisDriver:
    def __init__(self):
        self.redis_url = f'redis://{redis_host}'
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
    
    async def set_key(self, key, value, ttl=3600):
        await self.redis_client.set(key, value)
        if ttl:
            await self.redis_client.expire(key, ttl)
        return True

    async def get_key(self, key):
        return await self.redis_client.get(key)