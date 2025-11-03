# db/postgres.py
import os
import json
from typing import List, Optional, Dict, Any
import asyncpg
from dotenv import load_dotenv
from .base import EvalDB
from ..models import EvalTestCase

load_dotenv()

class PostgresEvalDB(EvalDB):
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB", "agent_eval")
        )
        # Create table if not exists
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_cases (
                    test_id TEXT PRIMARY KEY,
                    input_prompt TEXT NOT NULL,
                    input_context JSONB,
                    agent_output TEXT,
                    expected_output TEXT,
                    status TEXT,
                    agent_version TEXT,
                    created_by TEXT,
                    tags JSONB,
                    tool_call_trace JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def save_test_case(self, test_case: EvalTestCase):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO test_cases (
                    test_id, input_prompt, input_context, agent_output, expected_output,
                    status, agent_version, created_by, tags, tool_call_trace
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (test_id) DO UPDATE SET
                    agent_output = EXCLUDED.agent_output,
                    expected_output = EXCLUDED.expected_output,
                    tool_call_trace = EXCLUDED.tool_call_trace
            """,
                test_case.test_id,
                test_case.input_prompt,
                json.dumps(test_case.input_context or {}),
                test_case.agent_output,
                test_case.expected_output,
                test_case.status,
                test_case.agent_version,
                test_case.created_by,
                json.dumps(test_case.tags),
                json.dumps([r.model_dump() for r in test_case.tool_call_trace])
            )

    async def load_approved_test_cases(self, test_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            if test_ids:
                records = await conn.fetch("""
                    SELECT * FROM test_cases
                    WHERE status = 'approved' AND test_id = ANY($1)
                """, test_ids)
            else:
                records = await conn.fetch("""
                    SELECT * FROM test_cases WHERE status = 'approved'
                """)
            return [dict(record) for record in records]