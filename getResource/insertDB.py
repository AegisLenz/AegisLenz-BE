import pymongo
from dotenv import load_dotenv
import os
from getIAM import get_iam_users
from getS3 import get_s3_buckets
from getEC2 import get_ec2_instances

# .env 파일 로드
load_dotenv()

# MongoDB 연결 설정
mongo_host = os.getenv("MONGO_HOST")
mongo_port = os.getenv("MONGO_PORT")
mongo_database = os.getenv("MONGO_DATABASE")
mongo_username = os.getenv("MONGO_ROOT_USERNAME")
mongo_password = os.getenv("MONGO_ROOT_PASSWORD")

# MongoDB 클라이언트 생성
mongo_client = pymongo.MongoClient(
    host=mongo_host,
    port=int(mongo_port),
    username=mongo_username,
    password=mongo_password
)
db = mongo_client[mongo_database]
collection = db["resources"]

def insert_data(User_id):
    data = {
        "_id": User_id,
        "Resource": {
            "IamUser": get_iam_users(),
            "EC2": get_ec2_instances(),
            "S3_Bucket": get_s3_buckets()
        }
    }
    collection.update_one({"_id": "User_id"}, {"$set": data}, upsert=True)
    print("Data inserted/updated in MongoDB")

if __name__ == "__main__":
    User_id = input("Insert User_id? : ")
    print(get_iam_users())
    print(get_ec2_instances())
    print(get_s3_buckets())
    insert_data(User_id)