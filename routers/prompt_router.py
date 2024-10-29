from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from services import prompt_service
from schemas.prompt_schema import PromptChatRequestSchema, PromptChatStreamResponseSchema, CreatePromptResponseSchema

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/", response_model=CreatePromptResponseSchema)
async def create_prompt(prompt_service=Depends(prompt_service.PromptService)):
    prompt_id = await prompt_service.create_prompt()
    response = CreatePromptResponseSchema(prompt_id=prompt_id)
    return response


@router.post("/{prompt_session_id}/chat", response_model=PromptChatStreamResponseSchema)
async def chat_sse(prompt_session_id: str, request: PromptChatRequestSchema = Body(...), prompt_service=Depends(prompt_service.PromptService)):
    user_input = request.user_input
    return StreamingResponse(prompt_service.handle_chatgpt_conversation(user_input, prompt_session_id), media_type="text/event-stream")