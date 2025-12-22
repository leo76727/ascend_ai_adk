import pytest
import os
import sys
from eval_framework.adk_evaluator import AdkEvaluator

# Mocking Agent for Testing
class MockAgent:
    async def query(self, input_text):
        return f"Processed: {input_text}"

@pytest.mark.asyncio
async def test_adk_evaluator_flow():
    # Setup paths
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_dir = os.path.join(root_dir, "agents", "trader_agent")
    
    # Initialize
    evaluator = AdkEvaluator(model_name="gpt-4o") # Mock or use real
    
    # Check scan
    pairs = evaluator.scan_for_config_pairs(agents_dir)
    assert len(pairs) > 0, "Should find at least one evalset/config pair"
    
    # Check run (using a mock agent to avoid dependency issues in this unit test)
    # We won't load the real agent here to keep it fast/robust for this specific test
    mock_agent = MockAgent() 
    
    es_path, tc_path = pairs[0]  
    
    # Inject a simple mock evaluate_output to avoid paying LLM costs for this test run
    # or failing if no API key.
    original_eval = evaluator.evaluate_output
    async def mock_evaluate(input_text, actual_output, criteria, context={}):
        return 1.0, "Mock pass"
    
    evaluator.evaluate_output = mock_evaluate
    
    results = await evaluator.run_single_eval_set(es_path, tc_path, mock_agent)
    
    assert len(results) > 0
    assert results[0].status == "PASS"
    assert results[0].score == 1.0

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
