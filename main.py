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

@app.on_event("startup")
async def startup_event():
    await mongodb.connect()
    app.state.redis_driver = RedisDriver()
    await app.state.redis_driver.connect()
    app.state.es_service = ElasticsearchService()
    logger.info("Services initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    await mongodb.close()
    await app.state.redis_driver.close()
    await app.state.es_service.close_connection()
    logger.info("Services terminated.")