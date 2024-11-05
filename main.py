from fastapi import FastAPI
from routers import user_router, prompt_router, bert_router
from core.mongodb_driver import mongodb
from core.logging_config import setup_logger
from utils.insert_initial_data import insert_initial_data

logger = setup_logger()

app = FastAPI(root_path="/api/v1")

app.include_router(user_router.router)
app.include_router(prompt_router.router)
app.include_router(bert_router.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# 서버 시작 시 MongoDB 연결
@app.on_event("startup")
async def startup_db_client():
    await mongodb.connect()
    logger.info("MongoDB 연결이 설정되었습니다.")
    await insert_initial_data()

# 서버 종료 시 MongoDB 연결 종료
@app.on_event("shutdown")
async def shutdown_db_client():
    await mongodb.close()
    logger.info("MongoDB 연결이 종료되었습니다.")