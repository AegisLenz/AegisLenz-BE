import redis.asyncio as redis
import os
from dotenv import load_dotenv
import json

# 환경 변수 로드
load_dotenv()
redis_host = os.getenv("AEGISLENZ_REDIS_HOST", "aegislenz-redis")
redis_port = os.getenv("AEGISLENZ_REDIS_PORT", "6380")  # 포트 확인

class RedisDriver:
    def __init__(self):
        self.redis_url = f'redis://{redis_host}:{redis_port}'
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        print(f"Connected to Redis at {self.redis_url}")

    async def set_key(self, key, value):
        """
        Redis에 key-value 쌍을 영구적으로 저장하는 함수 (TTL 없음).
        """
        await self.redis_client.set(key, json.dumps(value))
        return True

    async def get_key(self, key):
        """
        Redis에서 특정 키에 대한 값을 가져오는 함수.
        """
        value = await self.redis_client.get(key)
        return json.loads(value) if value else None

    async def add_log_to_cluster(self, source_ip, log_data):
        """
        sourceIPAddress를 기준으로 로그를 클러스터링하여 Redis에 저장하는 함수.
        IP 주소를 키로 사용하여 해당 IP에 대한 모든 로그를 리스트 형태로 저장.
        """
        key = f"logs:{source_ip}"
        current_logs = await self.get_key(key) or []  # 현재 저장된 로그 가져오기
        current_logs.append(log_data)
        await self.set_key(key, current_logs)  # 클러스터링된 로그 저장