from pydantic import BaseModel
from odmantic import ObjectId
from typing import Optional
from datetime import datetime


class GetAllReportResponseSchema(BaseModel):
    report_ids: list[str]

    class Config:
        json_schema_extra = {
            "example": {
                "report_ids": [
                    "507f1f77bcf86cd799439011",
                    "507f191e810c19729de860ea",
                    "507f1f77bcf86cd799439012"
                ]
            }
        }


class GetReportResponseSchema(BaseModel):
    title: Optional[str] = None
    report_content: str
    report_id: ObjectId
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Title",
                "report_content": "# 공격 탐지 보고서\n\n## 공격 탐지 시간\n- **2024-12-10T20:35:52.619217**\n\n## 공격 유형\n- **Tactic**: TA0007 - Discovery\n- **Technique**: T1087 - Account Discovery\n\n## 공격 대상\n- EC2 인스턴스 ID: `i-07a8037419d0b5e6e`\n- IAM Role: `cg-ec2-mighty-role-iam_privesc_by_attachment_cgidlzglpea0c0`\n- 사용자: `qwer2`\n\n## 공격으로 탐지된 근거\n\n1. **2024-09-14T08:03:03Z**\n   - **이벤트**: DescribeInstanceCreditSpecifications\n   - **사용자**: Administrator\n   - **설명**: 인스턴스 `i-08f5648cfa2310089`에 대한 신용 사양 조회.\n\n2. **2024-09-14T08:03:05Z**\n   - **이벤트**: ListRoles\n   - **사용자**: qwer2\n   - **설명**: IAM 사용자 `qwer2`가 IAM 역할 목록 조회.\n\n3. **2024-09-14T08:03:06Z**\n   - **이벤트**: ListInstanceProfiles\n   - **사용자**: qwer2\n   - **설명**: IAM 사용자 `qwer2`가 인스턴스 프로파일 목록 조회.\n\n4. **2024-09-14T08:03:12Z**\n   - **이벤트**: DescribeInstances\n   - **사용자**: qwer2\n   - **설명**: 인스턴스 `i-08f5648cfa2310089`에 대한 세부정보 조회.\n\n5. **2024-09-14T08:03:14Z**\n   - **이벤트**: RemoveRoleFromInstanceProfile\n   - **사용자**: qwer2\n   - **설명**: 인스턴스 프로파일 `cg-ec2-meek-instance-profile-iam_privesc_by_attachment_cgidlzglpea0c0`에서 역할 제거.\n\n6. **2024-09-14T08:03:15Z**\n   - **이벤트**: AddRoleToInstanceProfile\n   - **사용자**: qwer2\n   - **설명**: 인스턴스 프로파일에 역할 추가.\n\n7. **2024-09-14T08:03:17Z**\n   - **이벤트**: RegisterManagedInstance\n   - **사용자**: qwer2\n   - **설명**: 관리되는 인스턴스 등록.\n\n8. **2024-09-14T08:03:19Z**\n   - **이벤트**: RunInstances\n   - **사용자**: qwer2\n   - **설명**: 새로운 EC2 인스턴스 `i-07a8037419d0b5e6e` 실행.\n\n9. **2024-09-14T08:03:22Z**\n   - **이벤트**: DescribeInstances\n   - **사용자**: qwer2\n   - **설명**: 인스턴스 `i-07a8037419d0b5e6e`에 대한 세부정보 조회.\n\n10. **2024-09-14T08:03:24Z**\n    - **이벤트**: AssumeRole\n    - **사용자**: EC2 서비스\n    - **설명**: 역할 `cg-ec2-mighty-role-iam_privesc_by_attachment_cgidlzglpea0c0`을 맡은 인스턴스.\n\n## 분석 및 결론\n로그에서 IAM 사용자 `qwer2`는 여러 번에 걸쳐 인스턴스를 조회하고, 역할을 인스턴스 프로파일에 추가 및 제거하며, 관리되는 인스턴스를 등록하는 행동을 보였습니다. 이러한 일련의 행동은 계정 탐지(T1087)와 발견(TA0007)과 관련된 공격 패턴을 제외하기 어려워 보입니다. 또한 특정 액세스 및 역할 조작은 계정 정보 수집 활동의 일부로 해석될 수 있습니다.\n\n따라서 해당 로그는 공격의 강력한 근거 자료로 간주될 수 있으며, 추가적인 세부 조사가 필요합니다.",
                "report_id": "675827b77f337c71ba90e629",
                "created_at": "2024-12-10T20:36:23.982000"
            }
        }


class CreateReportTemplateRequestSchema(BaseModel):
    title: Optional[str] = None
    selected_field: list
    prompt_text: str
