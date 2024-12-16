import json
import tiktoken

encoder = tiktoken.encoding_for_model("gpt-4")

def process_logs_by_token_limit(logs, token_limit=120000):
    """
    로그 데이터를 토큰 한계를 고려해 나눕니다.
    """
    processed_chunks = []
    current_chunk = []
    current_token_count = 0

    for log in logs:
        log_string = json.dumps(log)
        log_token_count = len(encoder.encode(log_string))

        if current_token_count + log_token_count > token_limit:
            print(f"청크 생성: 현재 청크 토큰 수 {current_token_count}, JSON 개수 {len(current_chunk)}")

            processed_chunks.append(current_chunk)
            current_chunk = []
            current_token_count = 0

        current_chunk.append(log)
        current_token_count += log_token_count

    if current_chunk:
        print(f"청크 생성: 현재 청크 토큰 수 {current_token_count}, JSON 개수 {len(current_chunk)}")
        processed_chunks.append(current_chunk)

    return processed_chunks
