import boto3
from dotenv import load_dotenv
import os
import json

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

def get_all_ec2_details():
    """모든 EC2 인스턴스와 관련된 추가 정보를 포함해 가져옵니다."""
    instances = ec2_client.describe_instances()["Reservations"]
    all_instance_details = []

    for reservation in instances:
        for instance in reservation["Instances"]:
            # 기본 인스턴스 정보
            instance_info = {
                "InstanceId": instance.get("InstanceId"),
                "InstanceType": instance.get("InstanceType"),
                "LaunchTime": instance.get("LaunchTime"),
                "State": instance["State"]["Name"],
                "PublicIpAddress": instance.get("PublicIpAddress"),
                "PrivateIpAddress": instance.get("PrivateIpAddress"),
                "VpcId": instance.get("VpcId"),
                "SubnetId": instance.get("SubnetId"),
                "SecurityGroups": instance.get("SecurityGroups"),
                "Tags": instance.get("Tags"),
                "EbsVolumes": [],
                "NetworkInterfaces": [],
                "IamInstanceProfile": instance.get("IamInstanceProfile"),
            }

            # EBS 볼륨 정보 가져오기
            for block in instance.get("BlockDeviceMappings", []):
                volume_id = block["Ebs"]["VolumeId"]
                volume_info = ec2_client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]
                instance_info["EbsVolumes"].append(volume_info)

            # 네트워크 인터페이스 정보 가져오기
            for ni in instance.get("NetworkInterfaces", []):
                network_info = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[ni["NetworkInterfaceId"]])["NetworkInterfaces"][0]
                instance_info["NetworkInterfaces"].append(network_info)

            all_instance_details.append(instance_info)
            print(json.dumps(instance_info, default=str, indent=4))

if __name__ == "__main__":
    get_all_ec2_details()