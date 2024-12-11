def filter_original_policy(original_policy, least_privilege_policy):
    """Original policy에 포함된 IAM 계정 중 least_privilege_policy에 해당하는 계정만 필터링합니다."""
    filtered_policy = {}

    # 사용자별로 original_policy를 필터링
    for user, user_policies in original_policy.items():
        if user in least_privilege_policy:
            filtered_policy[user] = user_policies

    return filtered_policy