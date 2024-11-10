from fastapi import HTTPException
from models.user_model import User
from core.mongodb_driver import mongodb  # MongoDB와의 연결을 담당하는 mongodb 인스턴스를 가져옴. DB 접속, 저장, 검색 가능
from models.asset_model import UserAsset  # UserAsset 모델. 자산 정보를 mongodb에 저장할 때 사용


#사용과와 관련된 데이터베이스 작업을 수행하는 함수를 포함함
class UserRepository:
    def __init__(self): #UserRepository 클래스의 인스턴스가 생성될 때 자동으로 실행됨
        self.user = User(name="John Doe", age=30, email="johndoe@example.com")  # 테스트 유저 데이터
        self.mongodb_engine = mongodb.engine
        self.mongodb_client = mongodb.client

    #비동기 함수. mongodb에 사용자를 저장하는 역할
    async def save_user(self, engine):
        new_user = await engine.save(self.user) #db에 사용자 저장이 완료될 때까지 기다림
        return new_user
    
    #비동기함수. user_id에 해당하는 사용자의 자산 정보를 조회하여 반환하는 역할
    async def get_user_asset(self, user_id: str, Assettype: str, engine):
        user_asset = await engine.find_one(UserAsset, {"user_id": user_id})
        if not user_asset:
            return {"error": "User asset not found"}

        # 반환 형식 { EC2 : [{}, {}, {}] }
        if Assettype == "EC2":
            return {"EC2": [ec2.dict() for ec2 in user_asset.asset.EC2]}
        elif Assettype == "S3_Bucket":
            return {"S3_Bucket": [bucket.dict() for bucket in user_asset.asset.S3]}
        elif Assettype == "IAMUser":
            return {"IAMUser": [iam.dict() for iam in user_asset.asset.IAM]}
        else:
            return {"error": "Invalid asset type specified"}
    
    # 사용자의 기존 정책을 가져오는 코드
    async def get_user_policies(self, user_id: str):
        try:
            user_asset = await self.mongodb_engine.find_one(
                UserAsset,
                UserAsset.user_id == user_id
            )
            # 각 IAM 유저의 AttachedPolicies를 추출하여 반환
            attached_policies_by_user = {
                iam.UserName: iam.AttachedPolicies for iam in user_asset.asset.IAM
            }
            return attached_policies_by_user
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while fetching messages: {str(e)}")
