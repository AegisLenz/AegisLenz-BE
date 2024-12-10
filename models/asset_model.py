from odmantic import Model, EmbeddedModel, Field
from typing import List, Optional
from datetime import datetime
from pydantic import ConfigDict


class AccessKey(EmbeddedModel):
    AccessKeyId: str
    Status: str
    LastUsedDate: Optional[datetime]

class IAMUser(EmbeddedModel):
    UserName: str
    UserId: str
    CreateDate: datetime
    UserPolicies: List[dict] = Field(default_factory=list)
    AttachedPolicies: List[dict] = Field(default_factory=list)
    Groups: List[str] = Field(default_factory=list)
    PasswordLastUsed: Optional[datetime]
    AccessKeysLastUsed: List[AccessKey] = Field(default_factory=list)
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
    Attachments: List[str] = Field(default_factory=list)
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
    SecurityGroups: List[dict] = Field(default_factory=list)
    Tags: List[dict] = Field(default_factory=list)
    EbsVolumes: List[EBSVolume]
    NetworkInterfaces: List[dict] = Field(default_factory=list)
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
    AssumeRolePolicyDocument: dict = Field(default_factory=dict)
    Description: Optional[str] = ""
    MaxSessionDuration: Optional[int] = 3600
    PermissionsBoundary: Optional[dict] = None
    Tags: Optional[List[dict]] = []
    AttachedPolicies: List[dict] = Field(default_factory=list)
    InlinePolicies: List[dict] = Field(default_factory=list)

class Asset(EmbeddedModel):
    IAM: List[IAMUser] = Field(default_factory=list)
    Role: List[Role] = Field(default_factory=list)
    EC2: List[EC2] = Field(default_factory=list)
    S3: List[S3_Bucket] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def validate(self):
        if not self.IAM and not self.Role and not self.EC2 and not self.S3:
            raise ValueError("Asset must have at least one non-empty field.")

class UserAsset(Model):
    user_id: str
    asset: Asset
    
    model_config = {"collection": "user_assets"}
