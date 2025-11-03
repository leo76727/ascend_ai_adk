class EvalError(Exception):
    """Base exception for eval framework"""
    pass

class ReplayError(EvalError):
    """Raised when a tool call cannot be replayed"""
    pass

class MCPError(EvalError):
    """Raised when MCP tool call fails"""
    pass