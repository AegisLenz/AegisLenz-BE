import os
import json
import asyncio
from typing import Optional, List, Dict, Any, Callable
import redis.asyncio as redis
from dotenv import load_dotenv
from common.logging import setup_logger

logger = setup_logger()

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

if not REDIS_HOST or not REDIS_PORT:
    raise ValueError("REDIS_HOST and REDIS_PORT must be set")

REDIS_KEY_PREFIX = {
    'LOGS': 'namespace:logs',
    'PROCESSED': 'namespace:processed',
    'PREDICTION': 'namespace:prediction'
}
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1


class RedisDriverError(Exception):
    """Redis 드라이버 오류."""
    pass


class RedisConnectionError(RedisDriverError):
    """Redis 연결 오류."""
    pass


class RedisOperationError(RedisDriverError):
    """Redis 작업 오류."""
    pass


class RedisDriver:
    def __init__(self):
        self.redis_url = f'redis://{REDIS_HOST}:{REDIS_PORT}'
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def connect(self):
        """Redis 연결 확인."""
        try:
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis.")
        except redis.ConnectionError as e:
            raise RedisConnectionError(f"Unable to connect to Redis: {e}")

    async def close(self):
        """Redis 연결 종료."""
        await self.redis_client.close()
        logger.info("Redis connection closed.")

    async def _execute_with_retry(self, operation: Callable[..., asyncio.Future], *args, **kwargs) -> Optional[Any]:
        """Redis 작업 재시도."""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                return await operation(*args, **kwargs)
            except redis.RedisError as e:
                logger.error(f"{operation.__name__} failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
        raise RedisOperationError(f"Redis operation failed after {MAX_RETRY_ATTEMPTS} attempts.")

    async def set_log_queue(self, source_ip: str, log_data: dict, max_logs: int = 5, ttl: int = 3600) -> None:
        """Redis 로그 큐에 로그 추가."""
        key = f"{REDIS_KEY_PREFIX['LOGS']}:{source_ip}"

        async def _set_operation():
            await self.redis_client.rpush(key, json.dumps(log_data))
            if not await self.redis_client.ttl(key):
                await self.redis_client.expire(key, ttl)
            if await self.redis_client.llen(key) > max_logs:
                await self.redis_client.lpop(key)

        await self._execute_with_retry(_set_operation)

    async def set_bulk_logs(self, source_ip: str, logs: List[dict], ttl: int = 3600):
        """Redis 로그 큐에 여러 로그 추가."""
        key = f"{REDIS_KEY_PREFIX['LOGS']}:{source_ip}"

        async def _bulk_operation():
            async with self.redis_client.pipeline() as pipe:
                for log_data in logs:
                    pipe.rpush(key, json.dumps(log_data))
                pipe.expire(key, ttl)
                await pipe.execute()

        await self._execute_with_retry(_bulk_operation)

    async def get_log_queue(self, source_ip: str) -> List[Dict]:
        """Redis 로그 큐에서 로그 가져오기."""
        key = f"{REDIS_KEY_PREFIX['LOGS']}:{source_ip}"

        async def _get_operation():
            logs = await self.redis_client.lrange(key, 0, -1)
            return [json.loads(log) for log in logs]

        return await self._execute_with_retry(_get_operation)

    async def mark_as_processed(self, source_ip: str, is_attack: bool = False) -> None:
        """로그 처리 표시."""
        key = f"{REDIS_KEY_PREFIX['PROCESSED']}:{source_ip}"

        async def _mark_operation():
            await self.redis_client.set(key, "true", ex=(None if is_attack else 3600))

        await self._execute_with_retry(_mark_operation)

    async def is_processed(self, source_ip: str) -> bool:
        """로그가 이미 처리되었는지 확인."""
        key = f"{REDIS_KEY_PREFIX['PROCESSED']}:{source_ip}"

        async def _check_operation():
            return await self.redis_client.exists(key)

        return await self._execute_with_retry(_check_operation)

    async def log_prediction(self, source_ip: str, prediction_data: dict) -> None:
        """예측 결과 저장."""
        key = f"{REDIS_KEY_PREFIX['PREDICTION']}:{source_ip}"

        async def _log_operation():
            await self.redis_client.set(key, json.dumps(prediction_data), ex=3600)

        await self._execute_with_retry(_log_operation)