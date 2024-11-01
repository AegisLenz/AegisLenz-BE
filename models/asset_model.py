from odmantic import Model, EmbeddedModel
from typing import List, Optional
from datetime import datetime

class AccessKey(EmbeddedModel):
    AccessKeyId: str
    Status: str
    LastUsedDate: Optional[datetime]

class IAMUser(EmbeddedModel):
    UserName: str
    UserId: str
    CreateDate: datetime
    UserPolicies: List[str]
    AttachedPolicies: List[str]
    Groups: List[str]
    AccessKeysLastUsed: List[AccessKey]
    LastUpdated: Optional[datetime]

class EBSVolume(EmbeddedModel):
    VolumeId: str
    Iops: Optional[int]
    VolumeType: str
    MultiAttachEnabled: bool
    Throughput: Optional[int]
    Size: Optional[int]
    SnapshotId: str
    AvailabilityZone: str
    State: str
    CreateTime: Optional[datetime]
    Attachments: List[str]
    Encrypted: bool

class EC2(EmbeddedModel):
    InstanceId: str
    InstanceType: Optional[str]
    LaunchTime: datetime
    State: Optional[str]
    PublicIpAddress: Optional[str]
    PrivateIpAddress: Optional[str]
    VpcId: Optional[str]
    SubnetId: Optional[str]
    SecurityGroups: List[dict]
    Tags: List[dict]
    EbsVolumes: List[EBSVolume]
    NetworkInterfaces: List[dict]
    IamInstanceProfile: Optional[dict]

class S3_Bucket(EmbeddedModel):
    Name: str
    CreationDate: Optional[datetime]
    Location: Optional[str]
    ACL: Optional[List[dict]]
    Policy: Optional[dict]
    Logging: Optional[dict]
    Versioning: Optional[str]
    Tags: Optional[List[dict]]

class Asset(EmbeddedModel):  # EmbeddedModel로 수정
    IAM: List[IAMUser]
    EC2: List[EC2]
    S3: List[S3_Bucket]

class UserAsset(Model):  # UserResource는 그대로 Model로 유지
    user_id: str
    resource: Asset  # 임베디드로 Resource 포함