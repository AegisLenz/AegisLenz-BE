from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from services import prompt_service

router = APIRouter(prefix="/prompt", tags=["prompt"])

@router.post("/chat")
async def chat_sse(user_input: dict = Body(...), prompt_service=Depends(prompt_service.PromptService)):
    user_message = user_input.get("user_input")
    return StreamingResponse(prompt_service.handle_chatgpt_conversation(user_message), media_type="text/event-stream")