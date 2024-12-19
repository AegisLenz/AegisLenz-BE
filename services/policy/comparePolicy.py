import fnmatch
from common.logging import setup_logger

logger = setup_logger()

def clustered_compare_policy(user_policies, clustered_policy_by_cloudtrail):
    if clustered_policy_by_cloudtrail is None:
        logger.error("clustered_policy_by_cloudtrail is None. It must be a dictionary.")
        raise ValueError("clustered_policy_by_cloudtrail is None. It must be a dictionary.")
    
    # 타입 체크
    if not isinstance(clustered_policy_by_cloudtrail, dict):
        logger.error(f"Invalid type for clustered_policy_by_cloudtrail: {type(clustered_policy_by_cloudtrail)}")
        raise TypeError("clustered_policy_by_cloudtrail must be a dictionary.")

    logger.debug(f"Type of clustered_policy_by_cloudtrail: {type(clustered_policy_by_cloudtrail)}")
    logger.debug(f"clustered_policy_by_cloudtrail: {clustered_policy_by_cloudtrail}")
    
    should_remove_actions = {}
    for userName in clustered_policy_by_cloudtrail.keys():
        if userName == "root":
            user_policy = user_policies.get("root", {})
        else:
            user_policy = user_policies.get(userName, {})
        should_remove_action = comparePolicy(user_policy, clustered_policy_by_cloudtrail[userName])
        
        if userName not in should_remove_actions:
            should_remove_actions[userName] = []
        should_remove_actions[userName].append(should_remove_action)

    return should_remove_actions

def comparePolicy(userPolicy, policy_by_cloudTrail):
    # 삭제해야 할 Action 부분 반환
    least_privilege_action = set()
    should_remove_action = set()
    
    # CloudTrail 정책에서 최소 권한 액션 수집
    for policies in policy_by_cloudTrail:
        for statement in policies.get("PolicyDocument", {}).get("Statement", []):
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            for action in actions:
                least_privilege_action.add(action)
    
    # 사용자 정책과 최소 권한 액션 비교
    for policy in userPolicy:
        policy_document = policy.get("PolicyDocument", {})
        for statement in policy_document.get("Statement", []):
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            for action in actions:
                matched = any(
                    fnmatch.fnmatch(action, least_action) or least_action == '*'
                    for least_action in least_privilege_action
                )
                if not matched:
                    should_remove_action.add(action)

    return should_remove_action
