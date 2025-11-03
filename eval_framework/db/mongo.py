# db/mongo.py
import os
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from .base import EvalDB
from ..models import EvalTestCase

load_dotenv()

class MongoEvalDB(EvalDB):
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None

    async def connect(self):
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "agent_eval")
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db["test_cases"]
        # Create index
        await self.collection.create_index("test_id", unique=True)
        await self.collection.create_index("status")

    async def disconnect(self):
        if self.client:
            self.client.close()

    async def save_test_case(self, test_case: EvalTestCase):
        doc = test_case.model_dump()
        # MongoDB natively handles dict/list
        await self.collection.replace_one({"test_id": test_case.test_id}, doc, upsert=True)

    async def load_approved_test_cases(self, test_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        query = {"status": "approved"}
        if test_ids:
            query["test_id"] = {"$in": test_ids}
        cursor = self.collection.find(query)
        return [doc async for doc in cursor]