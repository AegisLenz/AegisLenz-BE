from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from common.logging import setup_logger
from database.mongodb_driver import mongodb
from database.redis_driver import RedisDriver
from services.es_service import ElasticsearchService
from routers import user_router, prompt_router, bert_router, policy_router, dashboard_router, report_router

logger = setup_logger()

app = FastAPI(root_path="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://184.73.1.236:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

routers = [user_router, prompt_router, bert_router, policy_router, dashboard_router, report_router]
for router in routers:
    app.include_router(router.router)

app.state.redis_driver = None
app.state.es_service = None

async def initialize_service(service_name, initializer):
    try:
        await initializer()
        logger.info(f"{service_name} 연결이 성공적으로 설정되었습니다.")
    except Exception as e:
        logger.error(f"{service_name} 초기화 중 오류 발생: {e}")

async def shutdown_service(service_name, closer):
    try:
        await closer()
        logger.info(f"{service_name} 연결이 성공적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"{service_name} 종료 중 오류 발생: {e}")

@app.on_event("startup")
async def startup_event():
    logger.info("애플리케이션 시작 중...")

    await initialize_service("MongoDB", mongodb.connect)

    try:
        redis_driver = RedisDriver()
        await redis_driver.connect()
        app.state.redis_driver = redis_driver
        logger.info("Redis 연결이 성공적으로 설정되었습니다.")
    except Exception as e:
        logger.error(f"Redis 초기화 중 오류 발생: {e}")

    try:
        es_service = ElasticsearchService()
        app.state.es_service = es_service
        logger.info("Elasticsearch 서비스가 성공적으로 초기화되었습니다.")
    except Exception as e:
        logger.error(f"Elasticsearch 초기화 중 오류 발생: {e}")

    logger.info("애플리케이션이 성공적으로 시작되었습니다.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("애플리케이션 종료 중...")

    await shutdown_service("MongoDB", mongodb.close)

    try:
        redis_driver = app.state.redis_driver
        if redis_driver:
            await redis_driver.close()
            logger.info("Redis 연결이 성공적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"Redis 종료 중 오류 발생: {e}")

    try:
        es_service = app.state.es_service
        if es_service:
            await es_service.close_connection()
            logger.info("Elasticsearch 연결이 성공적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"Elasticsearch 종료 중 오류 발생: {e}")

    logger.info("애플리케이션 종료가 완료되었습니다.")