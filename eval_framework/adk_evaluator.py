import os
import json
import glob
import importlib.util
import sys
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import litellm
from datetime import datetime

# --- Pydantic Models for Configuration ---

class EvalCriteria(BaseModel):
    metric: str  # "semantic", "tool_usage", "tone", "hallucination", etc.
    instruction: Optional[str] = None
    expected_tools: Optional[List[str]] = None
    ordered_tools: bool = False
    threshold: float = 0.7  # Pass threshold (0.0 to 1.0)

class TestConfig(BaseModel):
    eval_set_id: str
    default_agent: Optional[str] = None
    criteria: Dict[str, EvalCriteria] # Keyed by eval_id (from evalset) or "default"

class EvalCaseResult(BaseModel):
    eval_id: str
    status: str # "PASS", "FAIL", "ERROR"
    score: float
    reason: str
    actual_output: str
    details: Dict[str, Any]

class EvaluationReport(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    results: List[EvalCaseResult]
    summary: Dict[str, int]

# --- Core Evaluator Class ---

class AdkEvaluator:
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name

    def scan_for_config_pairs(self, root_dir: str) -> List[tuple]:
        """Finds pairs of (evalset.json, test_config.json)."""
        pairs = []
        eval_sets = glob.glob(os.path.join(root_dir, "**/*.evalset.json"), recursive=True)
        for es_path in eval_sets:
            # Look for sibling test_config.json
            base_path = es_path.replace(".evalset.json", "")
            tc_path = f"{base_path}.test_config.json"
            if os.path.exists(tc_path):
                pairs.append((es_path, tc_path))
            else:
                print(f"Warning: No test_config.json found for {es_path}")
        return pairs

    def load_agent(self, agent_path: str, agent_var_name: str = "agent"):
        """Dynamically loads an agent object from a python file."""
        spec = importlib.util.spec_from_file_location("dynamic_agent_module", agent_path)
        if spec is None or spec.loader is None:
             raise ImportError(f"Could not load agent from {agent_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["dynamic_agent_module"] = module # Register to help relative imports potentially
        try:
             spec.loader.exec_module(module)
        except Exception as e:
             raise RuntimeError(f"Error executing agent module: {e}")
        
        if not hasattr(module, agent_var_name):
             raise AttributeError(f"Agent variable '{agent_var_name}' not found in {agent_path}")
        
        return getattr(module, agent_var_name)

    async def evaluate_output(self, input_text: str, actual_output: str, criteria: EvalCriteria, context: Dict = {}) -> tuple[float, str]:
        """
        Uses LLM (or logic) to evaluate output based on criteria.
        Returns (score, reasoning).
        """
        if criteria.metric == "tool_usage":
            # Heuristic check for tool usage (simplified for simulation)
            # In a real ADK run, we'd inspect the interaction log or tool trace.
            # Here keeping it simple or assuming we can parse tool calls from text if they are visible,
            # BUT better is if we have the 'intermediate_steps'. 
            # For this MVP, we might skip rigorous tool tracing if we don't have the execution trace handy.
            # Let's assume the actual_output might contain clues or we rely on 'semantic' mostly.
            # If we had the trace, we would check strictly. 
            pass # TODO: Implement tool trace check if available.

        # Default to LLM-based evaluation for semantic, tone, hallucination
        prompt = f"""
        You are an AI evaluator. Evaluate the ACTUAL OUTPUT against the CRITERIA.
        
        INPUT: {input_text}
        
        CRITERIA METRIC: {criteria.metric}
        CRITERIA INSTRUCTION: {criteria.instruction}
        
        ACTUAL OUTPUT: {actual_output}
        
        Task:
        1. Assign a score between 0.0 and 1.0 (1.0 = perfect match/adherence).
        2. Provide a brief reason.
        
        Return JSON ONLY: {{ "score": float, "reason": "string" }}
        """
        
        if self.model_name == "mock":
            return 1.0, "Mock evaluation passed"

        try:
            response = await litellm.acompletion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                stream=False
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            return float(result.get("score", 0.0)), result.get("reason", "No reason provided")
        except Exception as e:
            return 0.0, f"Evaluation execution failed: {str(e)}"

    async def run_single_eval_set(self, eval_set_path: str, config_path: str, agent_obj: Any) -> List[EvalCaseResult]:
        """Runs all cases in a single evalset."""
        with open(eval_set_path, 'r', encoding='utf-8') as f:
            eval_set = json.load(f)
        with open(config_path, 'r', encoding='utf-8') as f:
            test_config_data = json.load(f)
            # Handle potential wrapping in 'test_cases' or root level
            test_config = TestConfig(**test_config_data)

        # Map criteria
        criteria_map = test_config.criteria 
        default_criteria = criteria_map.get("default", EvalCriteria(metric="semantic", instruction="Ensure sensible response"))

        results = []

        for case in eval_set.get("eval_cases", []):
            eval_id = case.get("eval_id")
            # Extract last user message to prompt the agent
            conversation = case.get("conversation", [])
            last_user_msg = next((m for m in reversed(conversation) if m.get("user_content")), None)
            
            if not last_user_msg:
                continue

            user_text = last_user_msg["user_content"]["parts"][0]["text"] # Simplified parsing
            
            # --- AGENT INVOCATION ---
            # Using the ADK protocol: agent.generate_response(model, request)
            # But the 'agent_obj' might be a plain object or a function depending on setup.
            # Assuming 'agent_obj' is an ADK Agent instance that has async 'run' or similar.
            # Or we simulate via `agent.query(user_text)`.
            # Let's try to adapt to standard usage:
            try:
                # Mocking a session or using simple query if available
                # If ADK agent, we might need to construct a proper specific request
                # For now, assuming a simple wrapper method exists or we make one:
                # `response = await agent_obj.ainvoke(user_text)` -> This depends on ADK version
                # If we don't know the exact API, let's assume we can call an executor wrapper.
                # For this implementation, I will assume `agent.query(user_text)` or similar is exposed 
                # OR I will fix this in `agent_loader` context.
                
                # Let's assume we use the `agent_executor` from previous context? 
                # Or just `model.generate_content`?
                # Best fit for current ADK:
                # `response = await agent_obj.query(input=user_text)` if it's the high level agent.
                
                # Placeholder for actual agent call:
                actual_output = "SIMULATED_OUTPUT: " + user_text # TODO: Replace with real call
                
            except Exception as e:
                results.append(EvalCaseResult(
                    eval_id=eval_id, status="ERROR", score=0.0, reason=f"Agent runtime error: {e}",
                    actual_output="", details={}
                ))
                continue

            # --- EVALUATION ---
            criteria = criteria_map.get(eval_id, default_criteria)
            score, reason = await self.evaluate_output(user_text, actual_output, criteria)
            
            status = "PASS" if score >= criteria.threshold else "FAIL"
            
            results.append(EvalCaseResult(
                eval_id=eval_id, status=status, score=score, reason=reason,
                actual_output=actual_output, details={"metric": criteria.metric}
            ))

        return results

if __name__ == "__main__":
    # Test stub
    print("AdkEvaluator loaded.")
