import json
import random
import string

def generate_random_sid():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


def load_json(file_path):
    """JSON 파일을 로드."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        return None

def extract_resource_from_log(log):
    """로그에서 리소스 이름을 추출."""
    return log.get("eventSource", "unknown").split(".")[0]

def generate_least_privilege_policy(actions, resources, effect="Allow"):
    """최소 권한 정책 생성."""
    return [
        {
            "Sid": generate_random_sid(),
            "Effect": effect,
            "Action": actions,
            "Resource": resources
        }
    ]

def merge_policies(policies):
    merged_policy = {
        "PolicyName": "Aegislenz-Least-Privilege-Policy",
        "PolicyDocument" :{
            "Version": "2012-10-17",
            "Statement": []
        }
    }
    resource_action_map = {}

    for policy in policies:
        for statement in policy.get("Statement", []):
            actions = statement.get("Action", [])
            resources = statement.get("Resource", [])
            actions = [actions] if isinstance(actions, str) else actions
            resources = [resources] if isinstance(resources, str) else resources

            for resource in resources:
                if resource not in resource_action_map:
                    resource_action_map[resource] = set(actions)
                else:
                    resource_action_map[resource].update(actions)

    for resource, actions in resource_action_map.items():
        merged_policy["PolicyDocument"]["Statement"].append({
            "Sid": generate_random_sid(),
            "Effect": "Allow",
            "Action": list(actions),
            "Resource": resource,
        })
    return merged_policy

def map_etc(event_source, event_name):
    """기본 정책 생성."""
    action = f"{event_source.split('.')[0]}:{event_name}"
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": generate_random_sid(),
                "Effect": "Allow",
                "Action": action,
                "Resource": "*",
            }
        ]
    }

    return policy