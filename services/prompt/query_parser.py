from datetime import datetime
from typing import Union
from elastic_transport import ObjectApiResponse


def convert_dates_in_query(query: dict) -> dict:
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


def parse_db_response(response: list) -> list:
    """
    재귀적으로 데이터를 탐색하여 최종 쿼리 결과 값을 추출한다.
    """
    if isinstance(response, list):  # 리스트인 경우, 각 항목을 재귀적으로 처리
        extracted = [parse_db_response(item) for item in response]
        return [val for sublist in extracted for val in (sublist if isinstance(sublist, list) else [sublist])]
    elif isinstance(response, dict):  # 딕셔너리인 경우, 값들을 재귀적으로 탐색
        if len(response) == 1 and next(iter(response.values())):
            return parse_db_response(next(iter(response.values())))
        else:
            return [parse_db_response(value) for value in response.values()]
    else:  # 기본 데이터 타입 (문자열, 숫자 등) 처리
        return response


def parse_es_response(response: ObjectApiResponse) -> Union[dict, list]:
    """
    Elasticsearch 응답 데이터를 처리하여 의미 있는 결과를 반환한다.
    """
    if "aggregations" in response:
        result = {}
        for key, agg in response["aggregations"].items():
            if "buckets" in agg:  # Bucket aggregation 처리 (terms, histogram 등)
                result[key] = [
                    {"key": bucket["key"], "doc_count": bucket["doc_count"]}
                    for bucket in agg["buckets"]
                ]
            elif "value" in agg:  # 단일 값 aggregation 처리 (sum, avg 등)
                result[key] = agg["value"]
            else:  # 알려지지 않은 aggregation 처리
                result[key] = agg
        return result
    elif "hits" in response and "hits" in response["hits"]:
        documents = response["hits"]["hits"]
        return [doc["_source"] for doc in documents if "_source" in doc]
    else:
        raise ValueError(f"Unexpected Elasticsearch response structure: {response}")
