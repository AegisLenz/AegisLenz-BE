from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from services import prompt_service
from schemas.prompt_schema import PromptChatRequestSchema, PromptChatStreamResponseSchema

router = APIRouter(prefix="/prompt", tags=["prompt"])

@router.post("/{prompt_id}/chat", response_model=PromptChatStreamResponseSchema)
async def chat_sse(prompt_id: int, request: PromptChatRequestSchema = Body(...), prompt_service=Depends(prompt_service.PromptService)):
    user_input = request.user_input
    return StreamingResponse(prompt_service.handle_chatgpt_conversation(user_input, prompt_id), media_type="text/event-stream")