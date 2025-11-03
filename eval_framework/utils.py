import hashlib
import json
from copy import deepcopy
from typing import Any, Dict

def normalize_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove non-deterministic keys for hashing"""
    args = deepcopy(args)
    for key in ["as_of", "timestamp", "request_id", "now"]:
        args.pop(key, None)
    return args

def hash_dict(d: Dict[str, Any]) -> str:
    """Deterministic hash of a dict"""
    normalized = normalize_args(d)
    serialized = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode()).hexdigest()[:16]

def redact_sensitive(obj: Any) -> Any:
    """Recursively redact sensitive fields"""
    SENSITIVE_KEYS = {"client_id", "client_name", "account_number", "name", "email"}
    
    if isinstance(obj, dict):
        return {
            k: "[REDACTED]" if k in SENSITIVE_KEYS else redact_sensitive(v)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [redact_sensitive(item) for item in obj]
    return obj