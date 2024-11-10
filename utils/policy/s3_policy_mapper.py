# policy/s3_policy_mapper.py
from policy.common_utils import generate_least_privilege_policy

def s3_policy_mapper(log, policy_data):
    """S3 정책 생성."""
    request_params = log.get("requestParameters") or {}

    mapping = {
        "bucket_name": request_params.get("bucketName", None),
        "object_key": request_params.get("key", None),
        "key_prefix": request_params.get("keyPrefix", None)
    }

    resource_list = []
    for statement in policy_data.get("policy", []):
        for resource in statement.get("Resource", []):
            original_resource = resource
            for key, value in mapping.items():
                if value:
                    resource = resource.replace(f"{{{key}}}", value)

            if "{" in resource and "}" in resource:  # 매핑되지 않은 변수가 남아있는 경우
                resource_list.append("*")  # 모든 리소스를 지정
            else:
                resource_list.append(resource)

    # 최소 권한 정책 생성
    actions = policy_data.get("policy", [{}])[0].get("Action", [])
    least_privilege_policies = generate_least_privilege_policy(actions, resource_list)

    final_policy = {
        "Version": "2012-10-17",
        "Statement": least_privilege_policies
    }

    return final_policy

