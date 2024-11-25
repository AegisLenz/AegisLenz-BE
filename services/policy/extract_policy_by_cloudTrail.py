import os
from dotenv import load_dotenv
from services.policy.common_utils import load_json, merge_policies, map_etc
from services.policy.s3_policy_mapper import s3_policy_mapper
from services.policy.ec2_policy_mapper import ec2_policy_mapper
from services.policy.iam_policy_mapper import iam_policy_mapper

load_dotenv()


def clustering_by_username(logs):
    cluster = {}
    for log in logs:
        user_identity = log.get("userIdentity", {})
        user_name = user_identity.get("userName")
        if user_name not in cluster:
            cluster[user_name] = []
        cluster[user_name].append(log)
    return cluster


def making_policy(log_entry):
    """CloudTrail 로그의 이벤트 소스와 이벤트 이름에 따른 정책 생성."""
    event_source = log_entry.get("eventSource")
    event_name = log_entry.get("eventName")
    
    iam_policy_dir = os.getenv("IAM_POLICY_DIR_PATH")
    base_directory = os.path.join(iam_policy_dir, "AWSDatabase")

    # S3 관련 정책 매핑
    if event_source == 's3.amazonaws.com':
        specific_policy_path = os.path.join(base_directory, f'S3/{event_name.casefold()}.json')
        if os.path.exists(specific_policy_path):
            policy_data = load_json(specific_policy_path)
            policy = s3_policy_mapper(log_entry, policy_data)
        else:
            policy = map_etc(event_source, event_name)

    # EC2 관련 정책 매핑
    elif event_source == 'ec2.amazonaws.com':
        specific_policy_path = os.path.join(base_directory, f'EC2/{event_name.casefold()}.json')
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


def extract_policy_by_cloudTrail():
    # ES에서 가져와야 하는 로그. 일단 sample data로 대체
    iam_policy_dir = os.getenv("IAM_POLICY_DIR_PATH")
    file_path = os.path.join(iam_policy_dir, "src/sample_data/event_history.json")

    logs = load_json(file_path).get("Records", [])
    if not isinstance(logs, list):
        print("Error: The log file does not contain a valid list of log entries.")
        return
    
    normal_log = []
    all_policies = []
    policies = {}
    cluster = clustering_by_username(logs)
    for user_name in cluster:
        # Attack에서만 단독적으로 사용된 권한 제외
        for log_entry in cluster[user_name]:
            if not isinstance(log_entry, dict):
                print("Error: Log entry is not a valid dictionary.")
                continue

            isAttack = log_entry.get("mitreAttackTactics")
            policy = making_policy(log_entry)
            if policy:
                if isAttack is None:
                    normal_log.append(log_entry)
        
        # Attack 고려한 최소권한 추출
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

        if user_name not in policies:
            policies[user_name] = []
        policies[user_name].append(final_policy)
    return policies
