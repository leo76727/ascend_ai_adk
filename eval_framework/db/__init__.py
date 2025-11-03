# db/__init__.py
import os
from .base import EvalDB
from .postgres import PostgresEvalDB
from .mongo import MongoEvalDB

def create_eval_db() -> EvalDB:
    db_type = os.getenv("DATABASE_TYPE", "postgres").lower()
    if db_type == "postgres":
        return PostgresEvalDB()
    elif db_type == "mongo":
        return MongoEvalDB()
    else:
        raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}")

# Global instance (initialize on app startup)
eval_db: EvalDB = None