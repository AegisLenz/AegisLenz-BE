import json
import os

def cluster_logs_by_event_source_prefix(logs):
    """
    eventSource의 접두어로 로그를 클러스터링합니다.
    """
    clustered_logs = {}
    for record in logs.get('Records', []):
        event_source = record.get('eventSource', '')
        prefix = event_source.split('.')[0] if event_source else 'unknown'
        if prefix not in clustered_logs:
            clustered_logs[prefix] = []
        clustered_logs[prefix].append(record)
    return clustered_logs

def load_allow_actions(service_prefix, policy_path):
    """
    주어진 서비스 접두사(service prefix)에 해당하는 정책 파일을 불러옵니다.
    """
    file_path = os.path.join(policy_path, f"{service_prefix}.json")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            policy_data = json.load(file)
            allow_actions = policy_data.get('AllowActions', [])
            return allow_actions
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def filter_logs_by_allow_actions(clustered_logs, base_directory):
    """
    클러스터링된 로그의 eventName을 AllowActions에 따라 필터링합니다.
    """
    filtered_logs = {}
    
    for service_prefix, logs in clustered_logs.items():
        # AllowActions 가져오기
        allow_actions = load_allow_actions(service_prefix, base_directory)
        
        if not allow_actions:
            continue
        
        # AllowActions에 있는 eventName과 매칭되는 로그만 필터링
        filtered_logs[service_prefix] = [
            log for log in logs if log.get('eventName') in allow_actions
        ]

    return filtered_logs

def convert_clustered_logs_to_records_format(clustered_logs):
    """
    클러스터링된 로그를 하나의 'Records' 리스트로 변환합니다.
    """
    records = []
    for service_prefix, logs in clustered_logs.items():
        records.extend(logs)
    return {'Records': records}