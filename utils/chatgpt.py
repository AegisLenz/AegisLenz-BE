import os
import re
import json
import regex
import openai
from dotenv import load_dotenv
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch
from schemas.prompt_schema import PromptChatStreamResponseSchema
from core.redis_driver import RedisDriver

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
host_ip = os.getenv("HOST_IP")
elasticsearch_port = os.getenv("ELASTICSEARCH_PORT")
index_name = os.getenv("INDEX_NAME")

client = openai.OpenAI(api_key=api_key)
redis_client = RedisDriver()
es = AsyncElasticsearch(f"http://{host_ip}:{elasticsearch_port}")

def extract_dashboard_from_response(response):
    match = re.search(r'```python(.*?)```', response, re.DOTALL)
    if match:
        extracted_str = match.group(1).strip()
        return extracted_str
    else:
        return None


def extract_json_from_response(response):
    match = regex.search(r"\{(?:[^{}]|(?R))*\}", response)
    if match:
        json_str = match.group(0)
        try:
            json_obj = json.loads(json_str)
            return json_obj
        except json.JSONDecodeError:
            return None
    return None

def clean_streaming_chunk(chunk):
    """스트리밍 응답에서 필요 없는 부분을 제거한 후 반환"""
    choices = getattr(chunk, "choices", None)
    if choices and len(choices) > 0:
        delta = choices[0].delta
        if hasattr(delta, "content") and delta.content:
            return delta.content
    return ""

async def generate_response(user_input, prompt_id):
    # Redis에서 기존 대화 기록 가져오기
    conversation_key = f"chat:{prompt_id}"
    conversation_history = await redis_client.get_key(conversation_key)
    
    if conversation_history:
        conversation_history = json.loads(conversation_history)
    else:
        with open("utils/prompt.txt", "r", encoding="utf-8") as file:
            prompt_content = file.read()
        conversation_history = [{"role": "system", "content": prompt_content}]

    # 사용자 입력에 맞게 요청을 구성
    query = f"사용자의 자연어 질문: {user_input}"
    conversation_history.append({"role": "user", "content": query})

    # 대화 히스토리가 너무 길어지지 않도록 관리
    if len(conversation_history) > 10:
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
    for chunk in stream:
        clean_answer = clean_streaming_chunk(chunk)
        if clean_answer:
            full_response += clean_answer
            response = PromptChatStreamResponseSchema(status="processing", type="ElasticSearch", data=clean_answer)
            yield json.dumps(response.dict(), ensure_ascii=False) + "\n"

    # ChatGPT API의 응답값에서 ES 쿼리만 파싱하여 ELK 서버의 Elasticsearch에 쿼리 전송
    es_query = extract_json_from_response(full_response)
    if es_query:
        try:
            result = await es.search(index=index_name, body=es_query)  # 비동기 호출로 변경
            result_data = json.dumps(result['hits']['hits'], ensure_ascii=False)
            full_response += result_data
            response = PromptChatStreamResponseSchema(status="processing", type="ElasticSearchQueryResult", data=result_data)
            yield json.dumps(response.dict(), ensure_ascii=False) + "\n"
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        pass

    # 대시보드에 표시할 그래프 필터링
    dashboards = extract_dashboard_from_response(full_response)
    dashboards = json.dumps(dashboards, ensure_ascii=False)

    full_response += dashboards
    response = PromptChatStreamResponseSchema(status="processing", type="dashboard", data=dashboards)
    yield json.dumps(response.dict(), ensure_ascii=False) + "\n"

    # 스트리밍이 끝나면 전체 응답을 하나의 문자열로 히스토리에 저장
    conversation_history.append({"role": "assistant", "content": full_response})
    await redis_client.set_key(conversation_key, json.dumps(conversation_history, ensure_ascii=False))

    # 스트리밍 완료 메시지 전송
    response = PromptChatStreamResponseSchema(status="complete", data="Stream finished")
    yield json.dumps(response.dict(), ensure_ascii=False) + "\n"