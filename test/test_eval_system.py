import unittest
import asyncio
import os
import sys
from eval_framework.eval_system import EvalSystem

# Mock Agent
class MockAgent:
    async def query(self, input_text):
        return f"SIMULATED_OUTPUT: {input_text}"

class TestEvalSystem(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.sys_eval = EvalSystem(model_name="mock")

    def tearDown(self):
        self.loop.close()

    def test_eval_system_basic_flow(self):
        async def run_test():
            # Setup
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            agents_dir = os.path.join(root_dir, "agents", "trader_agent")
            
            # Scan for pairs manually to get a valid pair
            evaluator = self.sys_eval.evaluator
            pairs = evaluator.scan_for_config_pairs(agents_dir)
            self.assertGreater(len(pairs), 0, "Should find at least one evalset/config pair")
            
            es_path, tc_path = pairs[0]
            
            # Run evaluation
            agent = MockAgent()
            report = await self.sys_eval.run_evaluation(es_path, tc_path, agent)
            
            # Verify
            self.assertIsNotNone(report)
            self.assertGreater(len(report.results), 0)
            self.assertIn("PASS", report.summary)
            self.assertEqual(report.summary["PASS"] + report.summary["FAIL"] + report.summary["ERROR"], len(report.results))

        self.loop.run_until_complete(run_test())

    def test_eval_system_mcp_flow(self):
        async def run_test():
            # Test mcp execution (simulated)
            result = await self.sys_eval.run_mcp_evaluation(
                prompt="Tell me about TSLA RFQ",
                expected_output="Consider lowering barrier to 75% for TSLA. Adds ~1.2M vega. Historical win rate improves by 22%.",
                context={"underlying": "TSLA"}
            )
            
            self.assertTrue(result.passed)
            self.assertGreaterEqual(result.similarity_score, 0.8)
            self.assertIn("TSLA", result.actual_output)

        self.loop.run_until_complete(run_test())

if __name__ == "__main__":
    unittest.main()
