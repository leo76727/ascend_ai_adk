import os
from pathlib import Path
import json
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

DB_PATH = os.getenv('POSITIONS_DB', str(ROOT / 'data' / 'positions.db'))
LOG_PATH = os.getenv('AUDIT_LOG', str(ROOT / 'data' / 'logs.json'))
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

PROMPT_TEMPLATES_PATH = ROOT / 'config' / 'prompt_templates.yaml'

def load_prompt_templates():
    try:
        with open(PROMPT_TEMPLATES_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

PROMPT_TEMPLATES = load_prompt_templates()
