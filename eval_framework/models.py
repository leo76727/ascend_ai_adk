from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ToolCallRecord(BaseModel):
    tool_id: str
    tool_name: str
    args: Dict[str, Any]
    result: Any
    timestamp: str

class EvalTestCase(BaseModel):
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    input_prompt: str
    input_context: Optional[Dict[str, Any]] = None
    agent_output: str
    expected_output: str
    status: str = "draft"  # draft, approved, rejected
    agent_version: str
    created_by: str
    tags: List[str] = []
    tool_call_trace: List[ToolCallRecord] = []

class CaptureRequest(BaseModel):
    prompt: str
    context: Optional[Dict[str, Any]] = None
    user_email: str
    agent_version: str
    tags: List[str] = []

class CaptureResponse(BaseModel):
    test_id: str
    agent_output: str

class RunEvalRequest(BaseModel):
    agent_version: str
    test_ids: Optional[List[str]] = None

class EvalResult(BaseModel):
    test_id: str
    passed: bool
    similarity_score: float
    actual_output: str
    expected_output: str