import openai
from dotenv import load_dotenv
import os
import json

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)

with open("utils/prompt.txt", "r", encoding="utf-8") as file:
    prompt_content = file.read()

conversation_history = [{"role": "system", "content": prompt_content}]

async def generate_response(user_input):
    global conversation_history

    # 프롬프트 엔지니어링을 통해 요청을 구성
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

    # 스트리밍 응답 처리
    for chunk in stream:
        choices = getattr(chunk, "choices", None)
        if choices and len(choices) > 0:
            delta = choices[0].delta
            if hasattr(delta, "content") and delta.content:
                clean_answer = delta.content.replace("```", "").replace("'''", "").replace('"', '').strip()
                conversation_history.append({"role": "assistant", "content": clean_answer})
                yield json.dumps({"status": "processing", "data": clean_answer}, ensure_ascii=False) + "\n"

    yield json.dumps({"status": "complete", "data": "Stream finished"}, ensure_ascii=False) + "\n"