from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from db import create_eval_db, eval_db
from models import CaptureRequest, CaptureResponse, RunEvalRequest, EvalResult
from agent_executor import AsyncMCPTracingExecutor
import logging
import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from .models import CaptureRequest, CaptureResponse, RunEvalRequest, EvalResult
from .agent_executor import AsyncMCPTracingExecutor
from .exceptions import EvalError, ReplayError, MCPError

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_eval")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global eval_db
    eval_db = create_eval_db()
    await eval_db.connect()
    logger.info(f"Connected to {os.getenv('DATABASE_TYPE', 'postgres')}")
    yield
    await eval_db.disconnect()

app = FastAPI(title="AI Agent Eval Framework", lifespan=lifespan)

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(EvalError)
async def eval_error_handler(request: Request, exc: EvalError):
    logger.error(f"Eval error: {exc}")
    return JSONResponse(status_code=400, content={"error": str(exc)})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unexpected server error")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.post("/eval/capture", response_model=CaptureResponse)
async def capture_test_case(request: CaptureRequest):
    logger.info(f"Capture request from {request.user_email}")
    try:
        executor = AsyncMCPTracingExecutor(agent_version=request.agent_version)
        agent_output = await executor.run_agent(request.prompt, request.context)
        
        from .models import EvalTestCase
        test_case = EvalTestCase(
            input_prompt=request.prompt,
            input_context=request.context,
            agent_output=agent_output,
            expected_output=agent_output,  # User can edit later
            agent_version=request.agent_version,
            created_by=request.user_email,
            tags=request.tags,
            tool_call_trace=executor.recorded_calls,
            status="draft"
        )
        await eval_db.save_test_case(test_case)
        
        logger.info(f"Saved test case {test_case.test_id}")
        return CaptureResponse(test_id=test_case.test_id, agent_output=agent_output)
        
    except MCPError as e:
        logger.error(f"MCP error: {e}")
        raise HTTPException(status_code=502, detail=f"MCP service error: {e}")
    except Exception as e:
        logger.exception("Capture failed")
        raise HTTPException(status_code=500, detail="Capture failed")

@app.post("/eval/run", response_model=list[EvalResult])
async def run_regression_eval(request: RunEvalRequest):
    logger.info(f"Running eval for version {request.agent_version}")
    try:
        test_records = await eval_db.load_approved_test_cases(request.test_ids)  # ← abstract        
        if not test_records:
            return []
            
        results = []
        for record in test_records:
            try:
                executor = AsyncMCPTracingExecutor(
                    mode="replay",
                    mock_responses=record["tool_call_trace"],
                    agent_version=request.agent_version
                )
                actual_output = await executor.run_agent(
                    record["input_prompt"],
                    record["input_context"]
                )
                # Simple exact match for demo; replace with semantic similarity
                similarity = 1.0 if actual_output.strip() == record["expected_output"].strip() else 0.0
                passed = similarity >= 0.99  # strict for demo
                
                results.append(EvalResult(
                    test_id=record["test_id"],
                    passed=passed,
                    similarity_score=similarity,
                    actual_output=actual_output,
                    expected_output=record["expected_output"]
                ))
            except ReplayError as e:
                results.append(EvalResult(
                    test_id=record["test_id"],
                    passed=False,
                    similarity_score=0.0,
                    actual_output=f"Replay error: {e}",
                    expected_output=record["expected_output"]
                ))
            except Exception as e:
                results.append(EvalResult(
                    test_id=record["test_id"],
                    passed=False,
                    similarity_score=0.0,
                    actual_output=f"Runtime error: {e}",
                    expected_output=record["expected_output"]
                ))
        logger.info(f"Eval completed: {len(results)} tests")
        return results
        
    except Exception as e:
        logger.exception("Eval run failed")
        raise HTTPException(status_code=500, detail=f"Eval run failed: {e}")



