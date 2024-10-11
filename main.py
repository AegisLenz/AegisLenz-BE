from fastapi import FastAPI
from routers import user_router, bert_router

app = FastAPI()

app.include_router(user_router.router)
app.include_router(bert_router.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}