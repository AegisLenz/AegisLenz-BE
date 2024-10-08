import openai
from dotenv import load_dotenv
import os
import json
from schemas.prompt_schema import PromptChatStreamResponseSchema
from core.redis_driver import RedisDriver

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)
redis_client = RedisDriver()


def clean_streaming_chunk(chunk):
    """스트리밍 응답에서 필요 없는 부분을 제거한 후 반환"""
    choices = getattr(chunk, "choices", None)
    if choices and len(choices) > 0:
        delta = choices[0].delta
        if hasattr(delta, "content") and delta.content:
            return delta.content.replace("```", "").replace("'''", "").replace('"', '').strip()
    return ""


async def generate_response(user_input, prompt_id):
    # Redis에서 기존 대화 기록 가져오기
    conversation_key = "chat:{prompt_id}"
    conversation_history = await redis_client.get_key(conversation_key)
    print("가져온 대화 내역: ", conversation_history)
    
    if conversation_history:
        conversation_history = json.loads(conversation_history)
    else:
        with open("utils/prompt.txt", "r", encoding="utf-8") as file:
            prompt_content = file.read()
        conversation_history = [{"role": "system", "content": prompt_content}]

    # 사용자 입력에 맞게 요청을 구성
    query = f"사용자의 자연어 질문: {user_input} 응답은 코드 블록이나 따옴표 없이 순수한 JSON 데이터만 포함해야 합니다."
    conversation_history.append({"role": "user", "content": query})

    # 대화 히스토리가 너무 길어지지 않도록 관리
    if len(conversation_history) > 5:
        conversation_history.pop(1)

    # ChatGPT API 호출
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation_history,
        stream=True,
    )

    # 전체 응답을 누적할 변수
    full_response = ""

    # 스트리밍 응답 처리
    async for chunk in stream:
        clean_answer = clean_streaming_chunk(chunk)
        if clean_answer:
            full_response += clean_answer
            response = PromptChatStreamResponseSchema(status="processing", data=clean_answer)
            yield json.dumps(response.dict(), ensure_ascii=False) + "\n"

    # 스트리밍이 끝나면 전체 응답을 하나의 문자열로 히스토리에 저장
    conversation_history.append({"role": "assistant", "content": full_response})
    await redis_client.set_key(conversation_key, json.dumps(conversation_history, ensure_ascii=False))

    # 스트리밍 완료 메시지 전송
    response = PromptChatStreamResponseSchema(status="complete", data="Stream finished")
    yield json.dumps(response.dict(), ensure_ascii=False) + "\n"