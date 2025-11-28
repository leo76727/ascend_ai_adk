import os
from pathlib import Path
import json
import traceback
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

DB_PATH = os.getenv('POSITIONS_DB', str(ROOT / 'data' / 'positions.db'))
LOG_PATH = os.getenv('AUDIT_LOG', str(ROOT / 'data' / 'logs.json'))
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

PROMPT_TEMPLATES_PATH = ROOT / 'config' / 'prompt_templates.yaml'
print(f'Loading prompt templates from: {PROMPT_TEMPLATES_PATH}')
def load_prompt_templates():
    try:
        with open(PROMPT_TEMPLATES_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        print(f'Failed to load prompt templates from: {PROMPT_TEMPLATES_PATH} with error: {traceback.format_exc()}')
        return {}

PROMPT_TEMPLATES = load_prompt_templates()

def main():
    print(f'LLM_PROVIDER: {LLM_PROVIDER}')
    print(f'DEEPSEEK_API_KEY: {DEEPSEEK_API_KEY}')
    print(f'PROMPT_TEMPLATES: {json.dumps(PROMPT_TEMPLATES, indent=2)}')
    print(f'Sales Manager: {PROMPT_TEMPLATES.get("sales_manager", {})}')
    print(f'Trader Manager: {PROMPT_TEMPLATES.get("trader_manager", {})}')
    print(f'DB_PATH: {DB_PATH}')

if __name__ == '__main__':
    main()