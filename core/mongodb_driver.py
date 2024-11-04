from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
import os
from dotenv import load_dotenv

load_dotenv()
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_PORT = os.getenv("MONGODB_PORT")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
MONGODB_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD")

class MongoDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance.mongodb_url = f"mongodb://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_HOST}:{MONGODB_PORT}/?authSource=admin"
            cls._instance.client = None
            cls._instance.engine = None
        return cls._instance
    
    async def connect(self):      
        # MongoDB 클라이언트 생성
        client = AsyncIOMotorClient(self.mongodb_url)
        self.client = client[MONGODB_DATABASE]

        # AIOEngine을 Motor 클라이언트와 연결
        self.engine = AIOEngine(client=client, database=MONGODB_DATABASE)
    
    async def close(self):
        if self.client:
            self.client.close()
        self.engine = None

    async def get_engine(self):
        yield self.engine
    

# 싱글턴 인스턴스 생성
mongodb = MongoDB()