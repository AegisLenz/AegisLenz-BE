import os
import json
import asyncio
from typing import Optional, List, Dict, Any
import redis.asyncio as redis
from dotenv import load_dotenv
from common.logging import setup_logger

logger = setup_logger()

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

REDIS_KEY_PREFIX = {
    'LOGS': 'logs',
    'PROCESSED': 'processed',
    'PREDICTION': 'prediction'
}
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1

class RedisDriverError(Exception):
    """Redis 드라이버 오류"""
    pass

class RedisConnectionError(RedisDriverError):
    """Redis 연결 오류"""
    pass

class RedisOperationError(RedisDriverError):
    """Redis 작업 오류"""
    pass

class RedisDriver:
    def __init__(self):
        self.redis_url = f'redis://{REDIS_HOST}:{REDIS_PORT}'
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        try:
            self.redis_client.ping()
            logger.info("Successfully connected to Redis.")
        except redis.ConnectionError:
            raise RedisConnectionError("Unable to connect to Redis.")

    async def _execute_with_retry(self, operation: callable, *args, **kwargs) -> Optional[Any]:
        """공통 에러 처리 및 재시도 로직"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                return await operation(*args, **kwargs)
            except redis.RedisError as e:
                logger.error(f"Redis operation failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
        raise RedisOperationError(f"Redis operation failed after {MAX_RETRY_ATTEMPTS} attempts.")

    async def set_log_queue(self, source_ip: str, log_data: dict, max_logs: int = 5) -> None:
        """Redis 큐에 로그를 추가하는 함수"""
        key = f"{REDIS_KEY_PREFIX['LOGS']}:{source_ip}"
        async def _set_operation():
            await self.redis_client.rpush(key, json.dumps(log_data))
            await self.redis_client.expire(key, 3600)
            if await self.redis_client.llen(key) > max_logs:
                await self.redis_client.lpop(key)
        await self._execute_with_retry(_set_operation)

    async def set_bulk_logs(self, logs: List[dict], source_ip: str, max_logs: int = 5) -> None:
        """Redis 큐에 다수의 로그를 일괄 추가"""
        key = f"{REDIS_KEY_PREFIX['LOGS']}:{source_ip}"
        async def _bulk_operation():
            pipeline = self.redis_client.pipeline()
            for log_data in logs:
                pipeline.rpush(key, json.dumps(log_data))
            await pipeline.execute()
            await self.redis_client.expire(key, 3600)
            while await self.redis_client.llen(key) > max_logs:
                await self.redis_client.lpop(key)

        try:
            await self._execute_with_retry(_bulk_operation)
        except RedisOperationError as e:
            logger.error(f"Error adding bulk logs for {source_ip}: {str(e)}")

    async def get_log_queue(self, source_ip: str) -> List[Dict]:
        """특정 IP의 Redis 큐에 쌓인 로그를 가져오는 함수"""
        key = f"{REDIS_KEY_PREFIX['LOGS']}:{source_ip}"
        async def _get_operation():
            logs = await self.redis_client.lrange(key, 0, -1)
            try:
                return [json.loads(log) for log in logs]
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from Redis: {e}")
                return []
        return await self._execute_with_retry(_get_operation)

    async def mark_as_processed(self, source_ip: str) -> None:
        """특정 IP의 로그를 처리 완료로 표시"""
        key = f"{REDIS_KEY_PREFIX['PROCESSED']}:{source_ip}"
        async def _mark_operation():
            await self.redis_client.set(key, "true", ex=3600)
        await self._execute_with_retry(_mark_operation)

    async def is_processed(self, source_ip: str) -> bool:
        """특정 IP의 로그가 처리 완료인지 확인"""
        key = f"{REDIS_KEY_PREFIX['PROCESSED']}:{source_ip}"
        async def _check_operation():
            return await self.redis_client.exists(key)
        try:
            return await self._execute_with_retry(_check_operation)
        except RedisOperationError as e:
            logger.error(f"Error checking processed status for IP {source_ip}: {str(e)}")
            return False

    async def log_prediction(self, source_ip: str, prediction_data: dict) -> None:
        """공격 예측 결과를 Redis에 저장하는 함수"""
        key = f"{REDIS_KEY_PREFIX['PREDICTION']}:{source_ip}"
        async def _log_operation():
            await self.redis_client.set(key, json.dumps(prediction_data), ex=3600)
            logger.info(f"Logged prediction for IP {source_ip}: {prediction_data}")
        await self._execute_with_retry(_log_operation)