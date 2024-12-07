import os
import json
import asyncio
import redis.asyncio as redis
from dotenv import load_dotenv
from common.logging import setup_logger

logger = setup_logger()

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

# 상수 정의
REDIS_KEY_PREFIX = {
    'LOGS': 'logs',
    'PROCESSED': 'processed',
    'PREDICTION': 'prediction'
}
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds

class RedisDriver:
    def __init__(self):
        self.redis_url = f'redis://{REDIS_HOST}:{REDIS_PORT}'
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def _execute_with_retry(self, operation: callable, *args, **kwargs):
        """공통 에러 처리 및 재시도 로직"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                return await operation(*args, **kwargs)
            except redis.RedisError as e:
                logger.error(f"Redis operation failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY)
        return None

    async def set_log_queue(self, source_ip: str, log_data: dict, max_logs: int = 5) -> None:
        """Redis 큐에 로그를 추가하는 함수"""
        key = f"{REDIS_KEY_PREFIX['LOGS']}:{source_ip}"
        
        async def _set_operation():
            await self.redis_client.rpush(key, json.dumps(log_data))
            if await self.redis_client.llen(key) > max_logs:
                await self.redis_client.lpop(key)

        await self._execute_with_retry(_set_operation)

    async def get_log_queue(self, source_ip):
        """
        특정 IP의 Redis 큐에 쌓인 로그를 가져오는 함수.
        """
        try:
            key = f"logs:{source_ip}"
            logs = await self.redis_client.lrange(key, 0, -1)
            return [json.loads(log) for log in logs]
        except Exception as e:
            logger.error(f"Error getting log queue for IP {source_ip}: {e}")
            return []

    async def mark_as_processed(self, source_ip):
        """
        특정 IP의 로그를 처리 완료로 표시.
        """
        try:
            key = f"processed:{source_ip}"
            await self.redis_client.set(key, "true", ex=3600)
        except Exception as e:
            logger.error(f"Error marking logs as processed for IP {source_ip}: {e}")

    async def is_processed(self, source_ip):
        """
        특정 IP의 로그가 처리 완료인지 확인.
        """
        try:
            key = f"processed:{source_ip}"
            return await self.redis_client.exists(key)
        except Exception as e:
            logger.error(f"Error checking processed status for IP {source_ip}: {e}")
            return False

    async def log_prediction(self, source_ip, prediction_data):
        """
        공격 예측 결과를 Redis에 저장하는 함수.
        """
        try:
            key = f"prediction:{source_ip}"
            await self.redis_client.set(key, json.dumps(prediction_data), ex=3600)
            logger.info(f"Logged prediction for IP {source_ip}: {prediction_data}")
        except Exception as e:
            logger.error(f"Error logging prediction for IP {source_ip}: {e}")