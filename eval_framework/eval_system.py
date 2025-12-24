import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from .adk_evaluator import AdkEvaluator, EvalCaseResult, EvaluationReport
from .agent_executor import AsyncMCPTracingExecutor
from .models import EvalTestCase, EvalResult

class EvalSystem:
    """
    Unified evaluation orchestrator that integrates agent execution and evaluation.
    """
    def __init__(self, model_name: str = "gpt-4o", agent_version: str = "v1"):
        self.evaluator = AdkEvaluator(model_name=model_name)
        self.agent_version = agent_version

    async def run_evaluation(
        self, 
        eval_set_path: str, 
        config_path: str, 
        agent_obj: Any
    ) -> EvaluationReport:
        """
        Runs evaluation for a specific eval set and configuration.
        """
        results = await self.evaluator.run_single_eval_set(eval_set_path, config_path, agent_obj)
        
        summary = {"PASS": 0, "FAIL": 0, "ERROR": 0}
        for res in results:
            summary[res.status] += 1
            
        return EvaluationReport(results=results, summary=summary)

    async def run_mcp_evaluation(
        self,
        prompt: str,
        expected_output: str,
        context: Optional[Dict[str, Any]] = None,
        mock_responses: Optional[List[Dict]] = None
    ) -> EvalResult:
        """
        Runs a single MCP-aware evaluation using the tracer/executor.
        """
        mode = "replay" if mock_responses else "capture"
        executor = AsyncMCPTracingExecutor(
            mode=mode,
            mock_responses=mock_responses,
            agent_version=self.agent_version
        )
        
        actual_output = await executor.run_agent(prompt, context)
        
        # Simple evaluation logic for now (can be expanded to use AdkEvaluator)
        similarity = 1.0 if actual_output.strip() == expected_output.strip() else 0.0
        passed = similarity >= 0.8 # Example threshold
        
        return EvalResult(
            test_id="manual_run",
            passed=passed,
            similarity_score=similarity,
            actual_output=actual_output,
            expected_output=expected_output
        )

if __name__ == "__main__":
    print("EvalSystem initialized.")