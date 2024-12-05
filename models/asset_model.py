from odmantic import Model, EmbeddedModel
from typing import List, Optional
from datetime import datetime


class AccessKey(EmbeddedModel):
    AccessKeyId: str
    Status: str
    LastUsedDate: Optional[datetime]

# class UserPolicy(EmbeddedModel):
#     PolicyName: str
#     PolicyDocument: dict

# class AttachedPolicy(EmbeddedModel):
#     PolicyName: str
#     PolicyDocument: dict

# class InlinePolicy(EmbeddedModel):
#     PolicyName: str
#     PolicyDocument: dict

class IAMUser(EmbeddedModel):
    UserName: str
    UserId: str
    CreateDate: datetime
    UserPolicies: List = []
    AttachedPolicies: List = []
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

class Role(EmbeddedModel):
    Path: str
    RoleName: str
    RoleId: str
    Arn: str
    CreateDate: datetime
    AssumeRolePolicyDocument: dict
    Description: Optional[str] = ""
    MaxSessionDuration: Optional[int] = 3600
    PermissionsBoundary: Optional[dict] = None
    Tags: Optional[List[dict]] = []
    AttachedPolicies: List = []
    InlinePolicies: List = []

class Asset(EmbeddedModel):
    IAM: List[IAMUser]
    Role: List[Role]
    EC2: List[EC2]
    S3: List[S3_Bucket]

class UserAsset(Model):
    user_id: str
    asset: Asset
    
    model_config = {"collection": "user_assets"}