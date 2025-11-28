import os
import sys
from pathlib import Path
from google.adk.agents import Agent, callback_context
from google.adk.models.llm_request import LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types
REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT_PARENT = REPO_ROOT.parent 
sys.path.insert(0, str(REPO_ROOT_PARENT))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import config

# --- 1. Interaction Logger (Callbacks) ---
def log_interaction(context: callback_context.CallbackContext, message: str):
    """Helper to add a message to the session's interaction log."""
    print(message) # For terminal debugging
    if "interaction_log" not in context.state:
        context.state["interaction_log"] = []
    context.state["interaction_log"].append(message)

def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
):
    log_interaction(callback_context, f"🧠 **Thinking...**\n(Sending to LLM)")
    return llm_request

def before_tool_callback(
    context: CallbackContext, llm_request: LlmRequest
):
    log_interaction(
        context,
        f"🛠️ **LLM Request Content:** `{llm_request.contents}`\n"
    )
    return llm_request

def after_tool_callback(
    context: CallbackContext, tool_response: dict
):
    log_interaction(
        context,
        f"✔️ **Tool Response:**\n"
        f"   ```json\n{tool_response}\n   ```"
    )
    return tool_response

def get_auth_headers(ctx :ReadonlyContext) -> dict[str, str]:
    header = {"Authorization: Bearer": ctx.state.get("user:bearer_token", "")} if ctx else {"no_token": "true"}
    return header

# --- 2. Tool Definitions ---
# Assuming MCP servers are running on default ports or as configured
# We reuse the same MCP servers as sale_agent for now
mcp_base_url = "http://127.0.0.1:8003"

client_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{mcp_base_url}/client",
    ),    
    header_provider=get_auth_headers
)

position_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{mcp_base_url}/position"
    )
)

quote_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{mcp_base_url}/quote"
    )
)

market_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{mcp_base_url}/market"
    )
)

product_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{mcp_base_url}/product"
    )
)

trade_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{mcp_base_url}/trade"
    )
)

# --- 3. Agent Definition ---
template_config = config.PROMPT_TEMPLATES.get("client_intelligence", {})
temperature = template_config.get("temperature", 0.5)
max_tokens = template_config.get("max_tokens", 4000)

generation_config = types.GenerateContentConfig(
    temperature=temperature,
    max_output_tokens=max_tokens
)

client_agent = Agent(
    name="client_intelligence_agent",
    instruction=template_config.get("prompt", ""),
    model=LiteLlm(model=config.LLM_PROVIDER),
    tools=[client_tool, position_tool, quote_tool, market_tool, product_tool, trade_tool],
    generate_content_config=generation_config,
)
