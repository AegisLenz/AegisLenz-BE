from fastapi import FastAPI
from common.logging import setup_logger
from database.mongodb_driver import mongodb
from database.redis_driver import RedisDriver
from services.es_service import ElasticsearchService
from routers import user_router, prompt_router, bert_router, policy_router

logger = setup_logger()

# FastAPI 앱 생성
app = FastAPI(root_path="/api/v1")

# 라우터 등록
app.include_router(user_router.router)
app.include_router(prompt_router.router)
app.include_router(bert_router.router)
app.include_router(policy_router.router)

# Redis 및 Elasticsearch 서비스 초기화
redis_driver = RedisDriver()
es_service = ElasticsearchService()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# 서버 시작 시 리소스 초기화
@app.on_event("startup")
async def startup_event():
    # MongoDB 연결
    await mongodb.connect()
    logger.info("MongoDB 연결이 설정되었습니다.")

    # Redis 연결 확인
    await redis_driver.connect()
    logger.info("Redis 연결이 설정되었습니다.")

    # Elasticsearch는 별도 초기화 없이 사용 가능 (이미 초기화됨)

# 서버 종료 시 리소스 정리
@app.on_event("shutdown")
async def shutdown_event():
    # MongoDB 연결 종료
    await mongodb.close()
    logger.info("MongoDB 연결이 종료되었습니다.")

    # Redis 연결 종료
    await redis_driver.close()
    logger.info("Redis 연결이 종료되었습니다.")

    # Elasticsearch 연결 종료
    await es_service.close_connection()
    logger.info("Elasticsearch 연결이 종료되었습니다.")