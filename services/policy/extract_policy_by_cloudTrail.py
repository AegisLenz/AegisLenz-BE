import os

from dotenv import load_dotenv
from services.policy.common_utils import load_json, merge_policies, map_etc
from services.policy.s3_policy_mapper import s3_policy_mapper
from services.policy.ec2_policy_mapper import ec2_policy_mapper
from services.policy.iam_policy_mapper import iam_policy_mapper
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from datetime import datetime, timedelta, timezone
from common.logging import setup_logger
import json

load_dotenv()


logger = setup_logger()

def clustering_by_username(logs):
    records = logs.get("Records",[])
    cluster = {}
    for record in records:
        userIdentity = record.get("userIdentity",{})
        if "userName" in userIdentity:
            userName = userIdentity["userName"]
        elif userIdentity.get("type") == "Root":
            userName = "root"
        else:
            userName = "unknown"

        if userName not in cluster:
            cluster[userName] = [] 
        cluster[userName].append(record)
    return cluster


def fetch_all_logs_with_scroll():

    es_host = os.getenv("ES_HOST")
    es_port = os.getenv("ES_PORT")
    es_index = os.getenv('ES_INDEX')

    if not es_host or not es_port:
        raise ValueError("ES_HOST and ES_PORT are not set in the .env file.")

    es = Elasticsearch(f"{es_host}:{es_port}", max_retries=10, retry_on_timeout=True, request_timeout=120)

    now = datetime.now(timezone.utc)  # 현재 시간
    past_90_days = now - timedelta(days=90)  # 90일 전 시간

    # Scroll API 설정. 필요한 필드만 가져오기
    query = {
        "_source": [
            "eventName",
            "eventSource",
            "resources",
            "userIdentity",
            "eventSource",
            "awsRegion",
            "requestParameters.vpcSet.items.vpcId",
            "responseElements.vpcPeeringConnectionId",
            "requestParameters.TransitGatewayMulticastDomainId",
            "requestParameters.ServiceId",
            "requestParameters.securityGroupIds",
            "requestParameters.ClientVpnEndpointId",
            "requestParameters.hostIds",
            "requestParameters.BucketName",
            "requestParameters.TransitGatewayAttachmentId",
            "requestParameters.RouteTableId",
            "requestParameters.subnetSet.items.subnetId",
            "requestParameters.volumeSet.items.volumeId",
            "requestParameters.imagesSet.items.imageId",
            "requestParameters.LaunchTemplateId",
            "requestParameters.KeyName",
            "requestParameters.Ipv6PoolId",
            "requestParameters.CoipPoolId",
            "requestParameters.AllocationId",
            "requestParameters.IamInstanceProfile.Arn",
            "requestParameters.LocalGatewayRouteTableId",
            "requestParameters.NetworkInterfaceId",
            "requestParameters.filter.Dimensions.Key",
            "requestParameters.CustomerGatewayId",
            "requestParameters.filterSet.items.name",
            "requestParameters.instanceId",
            "requestParameters.instancesSet.items.instanceId",
            "responseElements.instancesSet.items.instanceId",
            "requestParameters.SnapshotId",
            "requestParameters.TransitGatewayRouteTableId",
            "requestParameters.VpnGatewayId",
            "requestParameters.CapacityReservationId",
            "requestParameters.HostId",
            "requestParameters.PrefixListId",
            "requestParameters.FlowLogId",
            "requestParameters.ReservedInstancesId",
            "requestParameters.SpotFleetRequestId",
            "requestParameters.TrafficMirrorFilterId",
            "requestParameters.TrafficMirrorSessionId",
            "requestParameters.TrafficMirrorFilterRuleId",
            "requestParameters.TrafficMirrorTargetId",
            "requestParameters.InternetGatewayId",
            "requestParameters.TransitGatewayId",
            "requestParameters.VpnConnectionId",
            "requestParameters.CertificateAuthorityId",
            "requestParameters.BundleId",
            "requestParameters.NetworkAclId",
            "requestParameters.ReservedInstancesListingId",
            "requestParameters.key",
            "requestParameters.keyPrefix"
        ],
        "query": {
            "range": {
                "@timestamp": {
                    "gte": past_90_days.isoformat(),
                    "lte": now.isoformat(),
                    "format": "strict_date_optional_time"
                }
            }
        },
        "sort": [{"@timestamp": {"order": "asc"}}],
        "size": 1000  # 한 번에 가져올 문서 수
    }

    try:
        response = es.search(index=es_index, body=query, scroll="1m")
        scroll_id = response["_scroll_id"]
        logs = [hit["_source"] for hit in response["hits"]["hits"]]

        while True:
            scroll_response = es.scroll(scroll_id=scroll_id, scroll="1m")
            hits = scroll_response["hits"]["hits"]
            if not hits:
                break

            logs.extend([hit["_source"] for hit in hits])
        formatted_logs = {"Records": logs}        
        return formatted_logs

    except es_exceptions.ConnectionError as e:
        print(f"Elasticsearch connection error: {str(e)}")
        return []
    except es_exceptions.RequestError as e:
        print(f"Elasticsearch request error: {str(e)}")
        return []
    except Exception as e:
        print(f"Error fetching logs from Elasticsearch: {str(e)}")
        return []



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

    logs = fetch_all_logs_with_scroll()
    if not logs:
        logger.error("No logs were retrieved. The operation will be terminated.")
        return []
    
    if not isinstance(logs, dict):
        logger.error("The log file does not contain a valid list of log entries.")
        return []
    
    
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