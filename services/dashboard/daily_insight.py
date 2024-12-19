import json
import tiktoken

encoder = tiktoken.encoding_for_model("gpt-4-mini")


def process_logs_by_token_limit(logs, token_limit=120000):
    """
    로그 데이터를 토큰 한계를 고려해 나눕니다.
    """
    processed_chunks, current_chunk, current_token_count = [], [], 0

    for log in logs:
        log_string = json.dumps(log)
        log_token_count = len(encoder.encode(log_string))

        if current_token_count + log_token_count > token_limit:
            print(f"청크 생성: 현재 청크 토큰 수 {current_token_count}, JSON 개수 {len(current_chunk)}")

            processed_chunks.append(current_chunk)
            current_chunk, current_token_count = [], 0

        current_chunk.append(log)
        current_token_count += log_token_count

    if current_chunk:
        print(f"청크 생성: 현재 청크 토큰 수 {current_token_count}, JSON 개수 {len(current_chunk)}")
        processed_chunks.append(current_chunk)

    return processed_chunks

def summarize_logs(log_chunks, timestamps):
    """
    각 로그 청크를 요약하고 요약 결과를 반환합니다.
    """
    template_content = load_prompt(prompt_files["daily"])
    response_list = []

    for index, (chunk, timestamp) in enumerate(zip(log_chunks, timestamps), start=1):
        log_string = "\n".join(json.dumps(log) for log in chunk)
        formatted_prompt = template_content.format(logs=log_string, timestamp=timestamp)

        prompt_txt = {"daily": {"role": "system", "content": formatted_prompt}}

        title = f"**{timestamp}에 발생한 공격의 전후로그 분석**"

        try:
            response = text_response(client, "gpt-4o-mini", [prompt_txt["daily"]])
            if response:

                response_with_title = f"{title}\n\n{response}"
                response_list.append(response_with_title)
                print(f"Chunk {index} 처리 완료. 응답 추가됨.")
                print_response(f"Chunk {index} 요약", response)
                save_history([{"role": "chunk", "content": response}], "chunk_all.txt", append=True)
            else:
                print(f"Chunk {index} 처리 중 응답이 비어 있습니다.")
        except Exception as e:
            print(f"Chunk {index} 처리 중 오류 발생: {str(e)}")

    return response_list  # 처리된 요약을 반환