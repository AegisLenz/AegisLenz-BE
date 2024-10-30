import boto3
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# AWS 세션 설정
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# EC2 클라이언트 생성
ec2_client = session.client('ec2')

def get_ec2_instances():
    ec2_instances = []
    instances = ec2_client.describe_instances()["Reservations"]

    for reservation in instances:
        for instance in reservation["Instances"]:
            instance_data = {
                "InstanceId": instance["InstanceId"],
                "InstanceType": instance["InstanceType"],
                "LaunchTime": instance["LaunchTime"],
                "State": instance["State"]["Name"],
                "PublicIpAddress": instance.get("PublicIpAddress"),
                "PrivateIpAddress": instance.get("PrivateIpAddress"),
                "VpcId": instance.get("VpcId"),
                "SubnetId": instance.get("SubnetId"),
                "SecurityGroups": instance.get("SecurityGroups"),
                "Tags": instance.get("Tags"),
                "EbsVolumes": [],
                "NetworkInterfaces": [],
                "IamInstanceProfile": instance.get("IamInstanceProfile")
            }

            for block in instance.get("BlockDeviceMappings", []):
                volume_id = block["Ebs"]["VolumeId"]
                volume_info = ec2_client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]
                instance_data["EbsVolumes"].append(volume_info)

            for ni in instance.get("NetworkInterfaces", []):
                network_info = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[ni["NetworkInterfaceId"]])["NetworkInterfaces"][0]
                instance_data["NetworkInterfaces"].append(network_info)

            ec2_instances.append(instance_data)
    return ec2_instances