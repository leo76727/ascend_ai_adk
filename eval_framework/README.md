# AI Agent Evaluation Framework

A reproducible, async, MCP-aware evaluation system for AI trading agents.

## Features
- Capture real agent interactions with MCP tool calls
- Save as golden test cases
- Replay deterministically for regression testing
- Async support for LLM/MCP calls
- Snowflake-backed persistence
- Built-in redaction for PII

## Setup
1. `cp .env.example .env`
2. Fill in Snowflake credentials
3. `pip install -r requirements.txt`
4. `uvicorn main:app --reload`

## Endpoints
- `POST /eval/capture` – Save a new test case
- `POST /eval/run` – Run regression on approved tests

## Database Support
This framework supports **PostgreSQL** and **MongoDB**.

### PostgreSQL Setup
```env
DATABASE_TYPE=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=eval_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=agent_eval

DATABASE_TYPE=mongo
MONGO_URI=mongodb://localhost:27017
MONGO_DB=agent_eval

```
---

### ✅ Key Benefits
- **Zero code changes** to switch databases  
- **Same data model** in both (Pydantic ensures consistency)  
- **Async-native**: `asyncpg` and `motor` are fully async  
- **Idempotent writes**: `ON CONFLICT` (Postgres) / `upsert` (Mongo)  
- **Index-optimized**: fast lookup by `test_id` and `status`

---

### 🚀 How to Run
1. Set `DATABASE_TYPE=postgres` or `mongo` in `.env`  
2. Configure respective connection vars  
3. `pip install -r requirements.txt`  
4. `uvicorn main:app --reload`

The service will auto-connect to your chosen database on startup.
