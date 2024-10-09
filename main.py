from fastapi import FastAPI
from routers import user_router, prompt_router

app = FastAPI(root_path="/api/v1")

app.include_router(user_router.router)
app.include_router(prompt_router.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}