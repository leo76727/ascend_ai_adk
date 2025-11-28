import os
import sys
from pathlib import Path
from google.adk.agents import Agent, callback_context

# Ensure the repository root (parent of the `agents` folder) is on sys.path so
# top-level imports like `import config` work when this script is run from
# inside the `agents/` directory. We insert it at the front so it takes
# precedence over other paths.
REPO_ROOT = Path(__file__).resolve().parents[1]
print(f"REPO_ROOT: {REPO_ROOT}")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT.parent))
print(f"Updated sys.path: {sys.path}")

from google.adk.models import LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from google.adk.apps.app import EventsCompactionConfig
from config import config
from google.genai import types

print(f"Config: {config.LLM_PROVIDER}, API Key: {config.DEEPSEEK_API_KEY}")
print(f"Config: {config.PROMPT_TEMPLATES}")
os.environ["DEEPSEEK_API_KEY"] = config.DEEPSEEK_API_KEY

# --- 1. Interaction Logger (Callbacks) ---
# We now log interactions into the session state, not a global variable.
def log_interaction(context: callback_context.CallbackContext, message: str):
    """Helper to add a message to the session's interaction log."""
    print(message) # For terminal debugging
    if "interaction_log" not in context.state:
        context.state["interaction_log"] = []
    context.state["interaction_log"].append(message)

# Define ADK Callbacks
def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
):
    log_interaction(callback_context, f"🧠 **Thinking...**\n(Sending to Deepseek LLM)")
    return llm_request

def before_tool_callback(
    context: callback_context.CallbackContext, llm_request: LlmRequest
):
    log_interaction(
        context,
        f"🛠️ **LLM Request Content:** `{llm_request.contents}`\n"
    )
    return llm_request

def after_tool_callback(
    context: callback_context.CallbackContext, tool_response: dict
):
    log_interaction(
        context,
        f"✔️ **Tool Response:**\n"
        f"   ```json\n{tool_response}\n   ```"
    )
    return tool_response

# --- 3. Agent Definition (Same as before) ---
mcp_server_url = "http://127.0.0.1:9004/mcp"  # Adjust port if needed
superset_query_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_server_url
))

spec_mcp_server_url = "http://127.0.0.1:9005/mcp"  # Adjust port if needed
superset_spec_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=spec_mcp_server_url
))
#filtered_tools = [tool for tool in superset_tool.get_tools() if "delete" not in tool.name.lower() ]



temperature=config.PROMPT_TEMPLATES["sales_manager"].get("temperature", 0.5)
max_tokens=config.PROMPT_TEMPLATES["sales_manager"].get("max_tokens", 1500)
print(f"Using temperature: {temperature}, max_tokens: {max_tokens} for sales_manager agent")

generation_config = types.GenerateContentConfig(
    temperature=temperature,       # Lower temperature for more deterministic output
    max_output_tokens=max_tokens   # Limit the length of the response
)

root_agent = Agent(
    name="superset_copliot_agent",
    instruction=config.PROMPT_TEMPLATES.get("superset_agent", {}).get("prompt", ""),
    model=LiteLlm(model=config.LLM_PROVIDER),  #DeepseekModel(),
    tools=[superset_spec_tool, superset_query_tool],
    generate_content_config=generation_config
)

'''
    
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Trigger compaction every 3 new invocations.
        overlap_size=1          # Include last invocation from the previous window.
    ),

'''