from fastapi import FastAPI
from routers import user_router, prompt_router

app = FastAPI()

app.include_router(user_router.router)
app.include_router(prompt_router.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}