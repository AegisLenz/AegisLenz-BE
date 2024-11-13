import redis.asyncio as redis
import os
from dotenv import load_dotenv
import json
import asyncio

load_dotenv()
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")

class RedisDriver:
    def __init__(self):
        self.redis_url = f'redis://{redis_host}:{redis_port}'
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def set_log_queue(self, source_ip, log_data, max_logs=5):
        """
        Redis 큐에 로그를 추가하는 함수. 각 IP당 최대 max_logs개의 로그만 저장.
        """
        try:
            key = f"logs:{source_ip}"
            await self.redis_client.rpush(key, json.dumps(log_data))
            # 큐의 길이가 max_logs를 초과하면 가장 오래된 항목을 제거
            if await self.redis_client.llen(key) > max_logs:
                await self.redis_client.lpop(key)
        except Exception as e:
            print(f"Error setting log queue for IP {source_ip}: {e}")
            await asyncio.sleep(1)

    async def get_log_queue(self, source_ip):
        """
        특정 IP의 Redis 큐에 쌓인 로그를 가져오는 함수.
        """
        try:
            key = f"logs:{source_ip}"
            logs = await self.redis_client.lrange(key, 0, -1)
            return [json.loads(log) for log in logs]
        except Exception as e:
            print(f"Error getting log queue for IP {source_ip}: {e}")
            return []

    async def log_prediction(self, source_ip, prediction_data):
        """
        공격 예측 결과를 Redis에 저장하는 함수.
        """
        try:
            key = f"prediction:{source_ip}"
            await self.redis_client.set(key, json.dumps(prediction_data), ex=3600)
            print(f"Logged prediction for IP {source_ip}: {prediction_data}")
        except Exception as e:
            print(f"Error logging prediction for IP {source_ip}: {e}")
