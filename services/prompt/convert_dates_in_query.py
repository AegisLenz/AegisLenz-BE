from datetime import datetime


def convert_dates_in_query(query):
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
