from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from services.prompt_service import PromptService
from schemas.prompt_schema import PromptChatRequestSchema, GetPromptContentsResponseSchema, PromptChatStreamResponseSchema, CreatePromptResponseSchema, GetAllPromptResponseSchema

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/", response_model=CreatePromptResponseSchema)
async def create_prompt(user_id: str = "1", prompt_service: PromptService = Depends()):
    prompt_session_id = await prompt_service.create_prompt(user_id)
    response = CreatePromptResponseSchema(prompt_session_id=prompt_session_id)
    return response


@router.get("/", response_model=GetAllPromptResponseSchema)
async def get_all_prompt(user_id: str = "1", prompt_service: PromptService = Depends()):
    return await prompt_service.get_all_prompt(user_id)


@router.get("/{prompt_session_id}",  response_model=GetPromptContentsResponseSchema)
async def get_prompt_chats(prompt_session_id: str, prompt_service: PromptService = Depends()):
    return await prompt_service.get_prompt_chats(prompt_session_id)


@router.post("/{prompt_session_id}/chat", response_model=PromptChatStreamResponseSchema)
async def chat_sse(prompt_session_id: str, user_id: str = "1", request: PromptChatRequestSchema = Body(...), prompt_service: PromptService = Depends()):
    user_question = request.user_input
    return StreamingResponse(
        prompt_service.handle_chat(user_question, prompt_session_id, user_id),
        media_type="text/event-stream"
    )
