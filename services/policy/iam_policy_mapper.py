from services.policy.common_utils import extract_resource_from_log, generate_least_privilege_policy

def iam_map_resource(log):
    account_id = log.get("userIdentity", {}).get("accountId")
    user_name = log.get("userIdentity", {}).get("userName")
    resource_arn = f"arn:aws:iam::{account_id}:user/{user_name}"
    resource_list = [resource_arn]
    return resource_list

def iam_policy_mapper(log):
    resource = extract_resource_from_log(log)
    resource_list = iam_map_resource(log)
    event_name = log.get("eventName", "UnknownEvent")
    least_privilege_policies = generate_least_privilege_policy([f"{resource}:{event_name}"], resource_list)

    final_policy = {
        "Version": "2012-10-17",
        "Statement": least_privilege_policies
    }
    return final_policy
