from services.policy.common_utils import generate_least_privilege_policy

def ec2_map_resource(policy_data, log):
    """EC2 리소스를 로그에서 매핑."""
    mapping = {
        "account_id": (log.get("userIdentity") or {}).get("accountId", None),
        "peering_connection_id": (log.get("responseElements") or {}).get("vpcPeeringConnectionId", None),
        "vpc_id": ((log.get("requestParameters") or {}).get("vpcSet", {}).get("items", [{}])[0].get("vpcId", None)
                if isinstance((log.get("requestParameters") or {}).get("vpcSet"), dict) else None),
        "region": log.get("awsRegion", None),
        "transit_gateway_multicast_domain_id": (log.get("requestParameters") or {}).get("TransitGatewayMulticastDomainId", None),
        "service_id": (log.get("requestParameters") or {}).get("ServiceId", None),
        "security_group_id": (log.get("requestParameters") or {}).get("securityGroupIds", [None])[0],
        "client_vpn_endpoint_id": (log.get("requestParameters") or {}).get("ClientVpnEndpointId", None),
        "host_id": (log.get("requestParameters") or {}).get("hostIds", [None])[0],
        "bucket_name": (log.get("requestParameters") or {}).get("BucketName", None),
        "attachment_id": (log.get("requestParameters") or {}).get("TransitGatewayAttachmentId", None),
        "route_table_id": (log.get("requestParameters") or {}).get("RouteTableId", None),
        "subnet_id": ((log.get("requestParameters") or {}).get("subnetSet", {}).get("items", [{}])[0].get("subnetId", None)
                    if isinstance((log.get("requestParameters") or {}).get("subnetSet"), dict) else None),
        "volume_id": ((log.get("requestParameters") or {}).get("volumeSet", {}).get("items", [{}])[0].get("volumeId", None)
                    if isinstance((log.get("requestParameters") or {}).get("volumeSet"), dict) else None),
        "image_id": ((log.get("requestParameters") or {}).get("imagesSet", {}).get("items", [{}])[0].get("imageId", None)
                    if isinstance((log.get("requestParameters") or {}).get("imagesSet"), dict) else None),
        "launch_template_id": (log.get("requestParameters") or {}).get("LaunchTemplateId", None),
        "key_pair_name": (log.get("requestParameters") or {}).get("KeyName", None),
        "ipv6_pool_id": (log.get("requestParameters") or {}).get("Ipv6PoolId", None),
        "coip_pool_id": (log.get("requestParameters") or {}).get("CoipPoolId", None),
        "allocation_id": (log.get("requestParameters") or {}).get("AllocationId", None),
        "instance_profile_name": (log.get("requestParameters") or {}).get("IamInstanceProfile", {}).get("Arn", None),
        "local_gateway_route_table_id": (log.get("requestParameters") or {}).get("LocalGatewayRouteTableId", None),
        "network_interface_id": (log.get("requestParameters") or {}).get("NetworkInterfaceId", None),
        "object_key": (log.get("requestParameters") or {}).get("key", None),
        "object_key_prefix": (log.get("requestParameters") or {}).get("keyPrefix", None),
        "customer_gateway_id": (log.get("requestParameters") or {}).get("CustomerGatewayId", None),
        "parameter_name": (log.get("requestParameters") or {}).get("filterSet", {}).get("items", [{}])[0].get("name", None),
        "instance_id": (
            (log.get("requestParameters") or {}).get("instanceId") or
            ((log.get("requestParameters") or {}).get("instancesSet", {}).get("items", [{}])[0].get("instanceId", None)
            if isinstance((log.get("requestParameters") or {}).get("instancesSet"), dict) else None) or
            ((log.get("responseElements") or {}).get("instancesSet", {}).get("items", [{}])[0].get("instanceId", None)
            if isinstance((log.get("responseElements") or {}).get("instancesSet"), dict) else None)
        ),
        "snap_id": (log.get("requestParameters") or {}).get("SnapshotId", None),
        "snapshot_id": (log.get("requestParameters") or {}).get("SnapshotId", None),
        "transit_gateway_route_table_id": (log.get("requestParameters") or {}).get("TransitGatewayRouteTableId", None),
        "vpn_gateway_id": (log.get("requestParameters") or {}).get("VpnGatewayId", None),
        "capacity_reservation_id": (log.get("requestParameters") or {}).get("CapacityReservationId", None),
        "dedicated_host_id": (log.get("requestParameters") or {}).get("HostId", None),
        "prefix_list_id": (log.get("requestParameters") or {}).get("PrefixListId", None),
        "vpc_flow_log_id": (log.get("requestParameters") or {}).get("FlowLogId", None),
        "reserved_instances_id": (log.get("requestParameters") or {}).get("ReservedInstancesId", None),
        "spot_fleet_request_id": (log.get("requestParameters") or {}).get("SpotFleetRequestId", None),
        "traffic_mirror_filter_id": (log.get("requestParameters") or {}).get("TrafficMirrorFilterId", None),
        "traffic_mirror_session_id": (log.get("requestParameters") or {}).get("TrafficMirrorSessionId", None),
        "traffic_mirror_filter_rule_id": (log.get("requestParameters") or {}).get("TrafficMirrorFilterRuleId", None),
        "traffic_mirror_target_id": (log.get("requestParameters") or {}).get("TrafficMirrorTargetId", None),
        "internet_gateway_id": (log.get("requestParameters") or {}).get("InternetGatewayId", None),
        "transit_gateway_id": (log.get("requestParameters") or {}).get("TransitGatewayId", None),
        "vpn_connection_id": (log.get("requestParameters") or {}).get("VpnConnectionId", None),
        "certificate_authority_id": (log.get("requestParameters") or {}).get("CertificateAuthorityId", None),
        "bundle_task_id": (log.get("requestParameters") or {}).get("BundleId", None),
        "network_acl_id": (log.get("requestParameters") or {}).get("NetworkAclId", None),
        "reserved_instances_listing_id": (log.get("requestParameters") or {}).get("ReservedInstancesListingId", None)
}

    resource_list = []
    resources = log.get('resources', [])
    if resources:
        for resource in resources:
            if 'ARN' in resource:
                resource_list.append(resource['ARN'])
                return resource_list

    for statement in policy_data.get("policy", []):
        for resource in statement.get("Resource", []):
            original_resource = resource
            for key, value in mapping.items():
                if value:
                    resource = resource.replace(f"{{{key}}}", value)

            if "{" in resource and "}" in resource:
                resource_list.append("*")
            else:
                resource_list.append(resource)
    
    return resource_list

def ec2_policy_mapper(log, policy_data):
    resource_list = ec2_map_resource(policy_data, log)
    actions = policy_data.get("policy", [{}])[0].get("Action", [])
    least_privilege_policies = generate_least_privilege_policy(actions, resource_list)

    final_policy = {
        "Version": "2012-10-17",
        "Statement": least_privilege_policies
    }
    return final_policy
