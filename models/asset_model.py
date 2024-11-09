#AWS 자산(EC2, IAM 사용자, S3 버킷 등)의 구조를 정의하는 파일
#MongoDB에 각 자산의 세부 정보를 저장하기 위해 ODM(객체 데이터 매핑)을 사용해 모델을 정의하고 있다.
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
    PasswordLastUsed: Optional[datetime]
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

class UserAsset(Model):
    user_id: str
    asset: Asset
    
    model_config = {"collection": "user_assets"}