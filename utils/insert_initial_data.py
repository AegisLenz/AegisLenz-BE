import os
import json
from core.mongodb_driver import mongodb
from models.policy_model import Policy, PolicyAction

async def insert_initial_policy_data():
    mongodb_engine = mongodb.get_engine()

    # Policy 컬렉션에 데이터가 없으면 초기 데이터를 삽입
    document_count = await mongodb_engine.count(Policy)

    if document_count == 0:
        print("컬렉션이 비어 있습니다. 초기 데이터를 삽입합니다.")
        
        # 상위 디렉터리의 하위 디렉터리 목록 가져오기
        base_directory = "./iam-policy/AWSDatabase"  # submodule로 설정한 AWS 최소권한정책 DB
        directories = [d for d in os.listdir(base_directory) if os.path.isdir(os.path.join(base_directory, d))]

        # 각 디렉터리의 하위 파일 목록 가져오기 및 데이터 삽입
        for directory in directories:
            dir_path = os.path.join(base_directory, directory)
            files = os.listdir(dir_path)
            
            for file in files:
                file_path = os.path.join(dir_path, file)

                with open(file_path, 'r') as f:
                    try:
                        data = json.load(f)

                        policy_actions = [
                            PolicyAction(
                                Action=item["Action"],
                                Effect=item["Effect"],
                                Resource=item["Resource"]
                            ) for item in data["policy"]
                        ]
                        policy = Policy(
                            service=directory,
                            event_name=os.path.splitext(file)[0],
                            policy=policy_actions
                        )

                        await mongodb_engine.save(policy)
                        print(f"{file} 데이터를 MongoDB에 삽입했습니다.")
            
                    except json.JSONDecodeError as e:
                        raise json.JSONDecodeError(f"JSON 디코딩 오류: {file}", file, e.pos)
                    except KeyError as e:
                        raise KeyError(f"키 오류: {e} - {file}")
    else:
        print("컬렉션에 데이터가 이미 존재합니다. 초기 데이터 삽입을 생략합니다.")