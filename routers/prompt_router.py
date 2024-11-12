from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from services import prompt_service
from schemas.prompt_schema import PromptChatRequestSchema, GetPromptContentsResponseSchema, PromptChatStreamResponseSchema, CreatePromptResponseSchema, GetAllPromptResponseSchema

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/", response_model=CreatePromptResponseSchema)
async def create_prompt(prompt_service=Depends(prompt_service.PromptService)):
    prompt_session_id = await prompt_service.create_prompt()
    response = CreatePromptResponseSchema(prompt_session_id=prompt_session_id)
    return response


@router.get("/", response_model=GetAllPromptResponseSchema)
async def get_all_prompt(prompt_service=Depends(prompt_service.PromptService)):
    prompts = await prompt_service.get_all_prompt()
    response = GetAllPromptResponseSchema(prompt_ids=prompts)
    return response


@router.get("/{prompt_session_id}",  response_model=GetPromptContentsResponseSchema)
async def get_prompt_chats(prompt_session_id: str, prompt_service=Depends(prompt_service.PromptService)):
    return await prompt_service.get_prompt_chats(prompt_session_id)


@router.post("/{prompt_session_id}/chat", response_model=PromptChatStreamResponseSchema)
async def chat_sse(prompt_session_id: str, request: PromptChatRequestSchema = Body(...), prompt_service=Depends(prompt_service.PromptService)):
    user_question = request.user_input
    return StreamingResponse(
        prompt_service.handle_chat(user_question, prompt_session_id),
        media_type="text/event-stream"
    )
