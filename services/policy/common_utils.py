import json

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
            "Action": actions,
            "Resource": resources,
            "Effect": effect,
            "Sid": f"policy-{actions[0]}"
        }
    ]

def merge_policies(policies):
    """여러 정책을 병합."""
    merged_policy = {
        "Version": "2012-10-17",
        "Statement": []
    }
    action_resource_map = {}

    for policy in policies:
        for statement in policy.get("Statement", []):
            actions = statement.get("Action", [])
            resources = statement.get("Resource", [])
            actions = [actions] if isinstance(actions, str) else actions
            resources = [resources] if isinstance(resources, str) else resources

            for action in actions:
                if action not in action_resource_map:
                    action_resource_map[action] = set(resources)
                else:
                    action_resource_map[action].update(resources)

    for action, resources in action_resource_map.items():
        merged_policy["Statement"].append({
            "Sid": f"policy-{action}",
            "Action": action,
            "Resource": list(resources),
            "Effect": "Allow",
        })
    
    return merged_policy


def map_etc(event_source, event_name):
    """기본 정책 생성."""
    action = f"{event_source.split('.')[0]}:{event_name}"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": f"policy-{action}",
                "Action": action,
                "Resource": "*",
                "Effect": "Allow",
            }
        ]
    }
