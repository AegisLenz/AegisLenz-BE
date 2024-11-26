from datetime import datetime


def convert_dates_in_query(query):
    """
    주어진 MongoDB 쿼리에서 날짜 비교 연산자($lt, $lte, $gt, $gte)와 관련된 값이 ISO 8601 형식의 문자열이라면, 이를 datetime 객체로 변환합니다.
    """
    date_operators = {"$lt", "$lte", "$gt", "$gte"}  # MongoDB의 날짜 비교 연산자

    if isinstance(query, dict):
        for key, value in query.items():
            if key in date_operators and isinstance(value, str):
                try:
                    # ISO 8601 형식의 날짜 문자열을 datetime 객체로 변환
                    if "Z" in value:
                        query[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    else:
                        query[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass  # 변환 불가능한 경우 그대로 둠
            elif isinstance(value, dict):
                query[key] = convert_dates_in_query(value)
            elif isinstance(value, list):
                query[key] = [convert_dates_in_query(item) for item in value]
    return query


def extract_values(data):
    """
    재귀적으로 데이터를 탐색하여 최종 쿼리 결과 값을 추출한다.
    """
    if isinstance(data, list):
        # 리스트가 포함된 경우, 각 항목을 재귀적으로 처리
        extracted = [extract_values(item) for item in data]
        # 평탄화(flatten) 및 중복 제거
        return [val for sublist in extracted for val in (sublist if isinstance(sublist, list) else [sublist])]
    elif isinstance(data, dict):
        # 딕셔너리의 값들을 탐색
        if len(data) == 1 and next(iter(data.values())):  # 단일 키-값 조합 처리
            return extract_values(next(iter(data.values())))
        else:
            return [extract_values(value) for value in data.values()]
    else:
        # 기본값 (문자열, 숫자 등)
        return data
