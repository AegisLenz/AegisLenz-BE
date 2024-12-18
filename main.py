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

async def initialize_service(service_name, initializer, app_state_key=None):
    """
    공통 서비스 초기화 함수.
    :param service_name: 서비스 이름 (로깅 용도)
    :param initializer: 초기화 함수 (비동기)
    :param app_state_key: app.state에 저장할 키 (선택 사항)
    """
    try:
        result = await initializer()
        if app_state_key:
            app.state[app_state_key] = result
        logger.info(f"{service_name} 연결이 성공적으로 설정되었습니다.")
        return result
    except Exception as e:
        logger.error(f"{service_name} 초기화 중 오류 발생: {e}")
        return None

@app.on_event("startup")
async def startup_event():
    logger.info("애플리케이션 시작 중...")

    await initialize_service("MongoDB", mongodb.connect)

    await initialize_service(
        "Redis",
        lambda: RedisDriver().connect(),
        app_state_key="redis_driver"
    )

    await initialize_service(
        "Elasticsearch",
        lambda: ElasticsearchService(),
        app_state_key="es_service"
    )

    logger.info("애플리케이션이 성공적으로 시작되었습니다.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("애플리케이션 종료 중...")

    await shutdown_service("MongoDB", mongodb.close)

    await shutdown_service(
        "Redis",
        lambda: app.state.redis_driver.close() if app.state.get("redis_driver") else None
    )

    await shutdown_service(
        "Elasticsearch",
        lambda: app.state.es_service.close_connection() if app.state.get("es_service") else None
    )

    logger.info("애플리케이션 종료가 완료되었습니다.")

async def shutdown_service(service_name, closer):
    """
    공통 서비스 종료 함수.
    :param service_name: 서비스 이름 (로깅 용도)
    :param closer: 종료 함수 (비동기)
    """
    try:
        await closer()
        logger.info(f"{service_name} 연결이 성공적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"{service_name} 종료 중 오류 발생: {e}")