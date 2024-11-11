import os
from policy.common_utils import load_json, merge_policies, map_etc
from policy.s3_policy_mapper import s3_policy_mapper
from policy.ec2_policy_mapper import ec2_policy_mapper
from policy.iam_policy_mapper import iam_policy_mapper


def clustering_by_username(file_path):
    logs = load_json(file_path).get("Records",[])
    cluster = {}
    for log in logs:
        userIdentity = log.get("userIdentity",{})
        userName = userIdentity.get("userName")
        if userName not in cluster:
            cluster[userName] = [] 
        cluster[userName].append(log)

    return cluster


def making_policy(log_entry):
    """CloudTrail 로그의 이벤트 소스와 이벤트 이름에 따른 정책 생성."""
    event_source = log_entry.get("eventSource")
    event_name = log_entry.get("eventName")

    # S3 관련 정책 매핑
    if event_source == 's3.amazonaws.com':
        specific_policy_path = os.path.join("./AWSDatabase/S3", f'{event_name.casefold()}.json')
        if os.path.exists(specific_policy_path):
            policy_data = load_json(specific_policy_path)
            policy = s3_policy_mapper(log_entry, policy_data)
        else:
            policy = map_etc(event_source, event_name)

    # EC2 관련 정책 매핑
    elif event_source == 'ec2.amazonaws.com':
        specific_policy_path = os.path.join("./AWSDatabase/EC2", f'{event_name.casefold()}.json')
        if os.path.exists(specific_policy_path):
            policy_data = load_json(specific_policy_path)
            policy = ec2_policy_mapper(log_entry, policy_data)
        else:
            policy = map_etc(event_source, event_name)
                    
    # IAM 관련 정책 매핑
    elif event_source == 'iam.amazonaws.com':
        policy = iam_policy_mapper(log_entry)

    # 정의되지 않은 이벤트 소스에 대한 기본 정책 매핑
    else:
        policy = map_etc(event_source, event_name)

    return policy


# CloudTrail 로그 파일에서 최소 권한 정책을 추출하는 함수
def extract_policy_by_cloudTrail(file_path):
    logs = load_json(file_path).get("Records",[])
    if not isinstance(logs, list):
        print("Error: The log file does not contain a valid list of log entries.")
        return
    
    normal_log = []
    all_policies = []
    cluster = clustering_by_username(file_path)
    policies = {}
    for userName in cluster:
        #attack에서만 단독적으로 사용된 권한 제외
        for log_entry in cluster[userName]:
            if not isinstance(log_entry, dict):
                print("Error: Log entry is not a valid dictionary.")
                continue

            isAttack = log_entry.get("mitreAttackTactics")
            policy = making_policy(log_entry)
            if policy:
                if isAttack is None:
                    normal_log.append(log_entry)
        #Attack고려한 최소권한 추출
        for log_entry in normal_log:
            if not isinstance(log_entry, dict):
                print("Error: Log entry is not a valid dictionary.")
                continue

            policy = making_policy(log_entry)
            all_policies.append(policy)

        if not all_policies:
            print("No valid policies were generated.")
            return
        final_policy = merge_policies(all_policies)

        if userName not in policies:
            policies[userName] = []
        policies[userName].append(final_policy)
    return policies