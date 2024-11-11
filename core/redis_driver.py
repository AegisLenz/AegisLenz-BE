import redis.asyncio as redis
import os
import json
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")

class RedisDriver:
    def __init__(self):
        self.redis_url = f'redis://{redis_host}:{redis_port}'
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def set_key(self, key, value, ttl=3600):
        await self.redis_client.set(key, json.dumps(value))
        if ttl:
            await self.redis_client.expire(key, ttl)
        return True

    async def get_key(self, key):
        value = await self.redis_client.get(key)
        return json.loads(value) if value else None

    async def add_log_to_buffer(self, source_ip, log_data, buffer_size=5):
        """
        sourceIP 별로 로그를 클러스터링하여 Redis에 저장합니다.
        """
        buffer_key = f"log_buffer:{source_ip}"
        current_buffer = await self.get_key(buffer_key) or []

        # 새로운 로그 데이터를 버퍼에 추가하고, 버퍼 사이즈 유지
        current_buffer.append(log_data)
        if len(current_buffer) > buffer_size:
            current_buffer.pop(0)  # 버퍼 사이즈를 초과하면 가장 오래된 로그 제거

        # 업데이트된 버퍼를 Redis에 저장
        await self.set_key(buffer_key, current_buffer)

    async def get_logs_by_source_ip(self, source_ip):
        """
        특정 sourceIP의 로그 버퍼를 가져옵니다.
        """
        buffer_key = f"log_buffer:{source_ip}"
        return await self.get_key(buffer_key)

    async def get_all_buffers(self):
        """
        Redis에 저장된 모든 로그 버퍼를 가져옵니다.
        """
        keys = await self.redis_client.keys("log_buffer:*")
        buffers = {}
        for key in keys:
            source_ip = key.split(":")[1]
            buffers[source_ip] = await self.get_key(key)
        return buffers