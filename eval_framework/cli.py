import argparse
import asyncio
import sys
import os
from .adk_evaluator import AdkEvaluator

async def main():
    parser = argparse.ArgumentParser(description="Run ADK Agent Evaluations")
    parser.add_argument("--folder", type=str, required=True, help="Folder containing evalset.json and test_config.json files")
    parser.add_argument("--agent-path", type=str, required=True, help="Path to the agent.py file")
    parser.add_argument("--agent-name", type=str, default="root_agent", help="Variable name of the agent object in agent.py")
    parser.add_argument("--model", type=str, default="gpt-4o", help="Evaluator model name (LiteLLM compatible)")
    
    args = parser.parse_args()
    
    # 1. Initialize Evaluator
    evaluator = AdkEvaluator(model_name=args.model)
    
    # 2. Load Agent (Verify it loads)
    try:
        print(f"Loading agent from {args.agent_path} ({args.agent_name})...")
        agent_obj = evaluator.load_agent(args.agent_path, args.agent_name)
        print("Agent loaded successfully.")
    except Exception as e:
        print(f"Failed to load agent: {e}")
        sys.exit(1)
        
    # 3. Scan for tasks
    pairs = evaluator.scan_for_config_pairs(args.folder)
    if not pairs:
        print(f"No valid evalset/config pairs found in {args.folder}")
        sys.exit(0)
        
    print(f"Found {len(pairs)} evaluation sets to run.")
    
    # 4. Run Evaluations
    all_results = []
    failed_count = 0
    
    for es_path, tc_path in pairs:
        print(f"\nProcessing {os.path.basename(es_path)}...")
        results = await evaluator.run_single_eval_set(es_path, tc_path, agent_obj)
        all_results.extend(results)
        
        for res in results:
            print(f"  [{res.status}] {res.eval_id}: Score={res.score:.2f} | Reason={res.reason}")
            if res.status != "PASS":
                failed_count += 1

    # 5. Summary
    print("\n" + "="*30)
    print("EVALUATION SUMMARY")
    print("="*30)
    print(f"Total Cases: {len(all_results)}")
    print(f"Passed:      {len(all_results) - failed_count}")
    print(f"Failed:      {failed_count}")
    
    if failed_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
