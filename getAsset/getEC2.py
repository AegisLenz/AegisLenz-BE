#AWS EC2 인스턴스 정보를 가져오는 코드
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
    reservations = ec2_client.describe_instances()["Reservations"]

    for reservation in reservations:
        for instance in reservation["Instances"]:
            instance_info = {
                "InstanceId": instance.get("InstanceId", ""),
                "InstanceType": instance.get("InstanceType", ""),
                "LaunchTime": instance.get("LaunchTime", None),
                "State": instance.get("State", {}).get("Name", ""),
                "PublicIpAddress": instance.get("PublicIpAddress", None),
                "PrivateIpAddress": instance.get("PrivateIpAddress", None),
                "VpcId": instance.get("VpcId", ""),
                "SubnetId": instance.get("SubnetId", ""),
                "SecurityGroups": instance.get("SecurityGroups", []),  # 빈 리스트로 설정
                "Tags": instance.get("Tags", []),                      # 빈 리스트로 설정
                "EbsVolumes": [],                                      # 기본값: 빈 리스트
                "NetworkInterfaces": instance.get("NetworkInterfaces", []),  # 빈 리스트로 설정
                "IamInstanceProfile": instance.get("IamInstanceProfile", None)
            }

            # EBS 볼륨 정보 가져오기
            for block_device in instance.get("BlockDeviceMappings", []):
                ebs_info = block_device.get("Ebs", {})
                instance_info["EbsVolumes"].append({
                    "VolumeId": ebs_info.get("VolumeId", ""),
                    "Iops": ebs_info.get("Iops", None),
                    "VolumeType": ebs_info.get("VolumeType", ""),
                    "MultiAttachEnabled": ebs_info.get("MultiAttachEnabled", False),
                    "Throughput": ebs_info.get("Throughput", None),
                    "Size": ebs_info.get("Size", None),
                    "SnapshotId": ebs_info.get("SnapshotId", ""),
                    "AvailabilityZone": ebs_info.get("AvailabilityZone", ""),
                    "State": ebs_info.get("State", ""),
                    "CreateTime": ebs_info.get("CreateTime", None),
                    "Attachments": ebs_info.get("Attachments", []),
                    "Encrypted": ebs_info.get("Encrypted", False)
                })

            ec2_instances.append(instance_info)

    return ec2_instances