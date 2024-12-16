import json
import tiktoken

encoder = tiktoken.encoding_for_model("gpt-4")


def process_logs_by_token_limit(logs, token_limit):
    """
    로그 데이터를 지정된 토큰 제한으로 나누기
    """
    processed_chunks = []
    current_chunk = []
    current_token_count = 0

    for log in logs:
        log_string = json.dumps(log)
        log_token_count = len(encoder.encode(log_string))

        # 현재 청크가 토큰 한도를 초과하면 새 청크 생성
        if current_token_count + log_token_count > token_limit:
            processed_chunks.append(current_chunk)
            current_chunk = []
            current_token_count = 0

        current_chunk.append(log)
        current_token_count += log_token_count

    # 남아 있는 로그 추가
    if current_chunk:
        processed_chunks.append(current_chunk)

    return processed_chunks
